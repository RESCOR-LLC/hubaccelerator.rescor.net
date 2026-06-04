#!/usr/bin/env python3
"""
Convert SecurityHub findings to CSV and store in an S3 bucket

This program can be invoked as an AWS Lambda function or from the command line.
If invoked from the command line, an assumable role is required. If invoked
from Lambda no parameters are required.

hubaccelerator-export
       --role-arn=[assumeableRoleArn]
       --regions=[commaSeparatedRegionList]
       --bucket=[s3BucketName]
       --filters=[cannedFilterName|jsonObject]
"""

import json
import io
import argparse
import csv
import sys
import os
from hubaccelerator import objects as csvo
import logging
import traceback
import re

# Default regions in list and string form
_DEFAULT_REGION_STRING = ""
_DEFAULT_REGION_LIST = [] #_DEFAULT_REGION_STRING.split(",")

_DEFAULT_LOGGING_LEVEL = logging.INFO
""" Default logging level """

# Set up logging
logging.basicConfig(level=_DEFAULT_LOGGING_LEVEL)

# Retrieve the logging instance
_LOGGER = logging.getLogger()
_LOGGER.setLevel(_DEFAULT_LOGGING_LEVEL)
""" Initialized logging RootLogger instance """

################################################################################
####
################################################################################
def getFilters ( candidate = None ):
    """
    Process filters, which are specified as a JSON object or as a string, in 
    this case "HighActive." If the filter can't be parsed, a messagae is issued
    but a null filter is returned. 
    """
    if not candidate:
        filters = {}
    elif isinstance(candidate, dict):
        filters = candidate
    elif candidate != "HighActive":
        try:
            filters = json.loads(candidate)
        except Exception as thrown:
            _LOGGER.error(f'493020e filter parsing failed: {thrown}')
            filters = {}
    else:
        _LOGGER.info("493030i canned HighActive filter selects active high- " + \
            "and critical-severity findings")
        filters = {
            "SeverityLabel": 
            [ 
                {"Value": "CRITICAL", "Comparison": "EQUALS" }, 
                {"Value": "HIGH", "Comparison": "EQUALS"}
            ], 
            "RecordState": 
            [ 
                { "Comparison": "EQUALS", "Value": "ACTIVE"}
            ]
        }

    return filters

################################################################################
#### Invocation-independent process handler
################################################################################
def executor (role=None, region=None, filters=None, bucket=None, limit=0, 
    retain=False):
    """
    Carry out the actions necessary to download and export SecurityHub findings,
    whether invoked as a Lambda or from the command line.
    """
    # Auto-discover aggregation region and linked regions from Security Hub
    aggregator = csvo.HubActor.discoverAggregator(region=region, role=role)

    if aggregator:
        # Use discovered aggregator configuration
        if not region:
            region = aggregator['aggregationRegion']
        regions = aggregator['regions']
        _LOGGER.info(f'using Security Hub aggregator: home={aggregator["aggregationRegion"]}, '
            f'{len(regions)} region(s)')
    else:
        # Fall back to env/SSM/API region discovery
        regions = None
        env_regions = csvo.env("HUBACCELERATOR_REGIONLIST")
        if env_regions:
            regions = [r.strip() for r in env_regions.split(',') if r.strip()]

        if not regions:
            ssmActor = csvo.SsmActor(role=role, region=region)
            ssm_regions = getattr(ssmActor, "/csvManager/regionList", None)
            if ssm_regions:
                regions = [r.strip() for r in ssm_regions.split(',') if r.strip()]

        if not regions:
            regions = [region] if region else ['us-east-1']

        _LOGGER.info(f'no aggregator found — using regions: {regions}')

    # Get the SSM parameters and a client for further SSM operations
    ssmActor = csvo.SsmActor(role=role, region=region)

    # Get information about the bucket
    folder = getattr(ssmActor, "/csvManager/folder/findings", None)
    bucket = bucket if bucket else getattr(ssmActor, "/csvManager/bucket", None)

    _LOGGER.debug(f'493050d writing to s3://{bucket}/{folder}/*') 

    # A client to act on the bucket
    s3Actor = csvo.S3Actor(
        bucket=bucket, 
        folder=folder, 
        region=region, 
        role=role
    )

    # Create SecurityHub actor — use aggregation region as primary (first in list)
    # to ensure authorization works in a known-good region
    ordered_regions = [region] + [r for r in regions if r != region] if region else regions
    hubActor = csvo.HubActor(
        role=role,
        region=ordered_regions
    )

    # Obtain the findings for all applicable regions
    hubActor.downloadFindings(filters=filters,limit=limit)

    if hubActor.count <= 0:
        _LOGGER.warning("no findings downloaded")
        return {"success": True, "message": "No findings matched the filter", "count": 0}
    else:
        _LOGGER.info(f'preparing to write {hubActor.count} findings')

        # Build CSV in memory (avoids /tmp security concerns in Lambda)
        csvBuffer = io.StringIO()
        first = True

        for finding in hubActor.getFinding():
            findingObject = csvo.Finding(finding, actor=hubActor)

            if first:
                writer = csv.DictWriter(csvBuffer,
                    fieldnames=findingObject.columns)
                writer.writeheader()
                first = False

            writer.writerow(findingObject.rowMap)

        csvContent = csvBuffer.getvalue()
        csvBuffer.close()

        _LOGGER.info(f'findings serialized ({len(csvContent)} bytes)')

        # Upload directly to S3 from memory
        s3Actor.primaryClient.put_object(
            Bucket=s3Actor.bucket,
            Key=s3Actor.objectKey,
            Body=csvContent.encode('utf-8'),
        )

        _LOGGER.info(f'uploaded to s3://{s3Actor.bucket}/{s3Actor.objectKey}')

        # Optionally write a local copy
        if retain:
            localFile = s3Actor.filePath()
            with open(localFile, 'w') as f:
                f.write(csvContent)
            _LOGGER.info(f'local copy retained: {localFile}')

        # Return details to caller
        answer = {
            "success" : True ,
            "message" : "Export succeeded" ,
            "bucket" : s3Actor.bucket ,
            "exportKey" : s3Actor.objectKey
        }

        return answer
################################################################################
#### Lambda handler
################################################################################
def lambdaHandler ( event = None, context = None ):
    """
    Perform the operations necessary when hubaccelerator-export is invoked
    as a Lambda function.
    """
    # The event keys we care about are processed below
    role = event.get("role")
    region = event.get("region")
    filters = getFilters(event.get("filters", {}))
    bucket = event.get("bucket")
    retain = event.get("retainLocal", False)
    limit = event.get("limit", 0)
    eventData = event.get("event")

    # If no region is specified it must be obtains from the environments
    if not region:
        region = csvo.env("HUBACCELERATOR_REGION")
        _LOGGER.info(f"493130i obtained region {region} from environment")

    # This is where we will store the result
    answer = {}

    # Determine if Lambda was invoked manually or via an event
    if eventData:
        eventType = eventData.get("detail-type", "UNKNOWN")
        _LOGGER.info(f"493140i Lambda invoked by {eventType}")
    else:
        _LOGGER.info("493150i Lambda invoked extemporaneously")

    # Perform the real work
    try:
        result = executor(
            role=role,
            region=region,
            filters=filters,
            bucket=bucket,
            retain=retain,
            limit=limit
        )

        answer = {
            "message": result.get("message"),
            "bucket": result.get("bucket"),
            "exportKey": result.get("exportKey"),
            "resultCode": 200 if result.get("success") else 400
        }

    # Catnch any errors
    except Exception as thrown:
        errorType = type(thrown).__name__
        errorTrace = traceback.format_tb(thrown.__traceback__, limit=5)

        _LOGGER.error(f"493160e Lambda failed ({errorType}): {thrown}\n{errorTrace}")
        
        answer = { 
            "message" : thrown ,
            "traceback" : traceback.format_tb(thrown.__traceback__, limit=5),
            "bucket" : None ,
            "exportKey" : None ,
            "resultCode" : 500
        }

    return answer

################################################################################
#### Main body is invoked if this is a command invocation
################################################################################
def main():
    """CLI entry point for hubaccelerator-export."""
    try:
        parser = argparse.ArgumentParser(
            prog='hubaccelerator-export',
            description='Export AWS Security Hub findings to CSV. '
                'Defaults read from SSM Parameter Store (/csvManager/*).')
        parser.add_argument("--role-arn", required=False, dest="roleArn",
            help="Assumable role ARN (default: use environment credentials)")
        parser.add_argument("--filters", default='HighActive', required=False,
            help="Canned filter name or JSON filter object (default: HighActive)")
        parser.add_argument("--bucket", required=False,
            help="S3 bucket (default: from SSM /csvManager/bucket)")
        parser.add_argument("--limit", required=False, type=int, default=0,
            help="Max findings to retrieve (default: unlimited)")
        parser.add_argument("--retain-local", action="store_true",
            dest="retainLocal", default=False, help="Keep local CSV copy")
        parser.add_argument("--primary-region", "--region", dest="region",
            default=csvo.env("HUBACCELERATOR_REGION"),
            help="Primary AWS region (default: auto-discovered from Security Hub aggregator, "
                 "or HUBACCELERATOR_REGION env)")

        arguments = parser.parse_args()

        executor(
            role=arguments.roleArn,
            filters=getFilters(arguments.filters),
            bucket=arguments.bucket,
            limit=arguments.limit,
            retain=arguments.retainLocal,
            region=arguments.region
        )

    except Exception as thrown:
        _LOGGER.exception(f"unexpected error: {thrown}")
        sys.exit(1)

if __name__ == "__main__":
    main()
