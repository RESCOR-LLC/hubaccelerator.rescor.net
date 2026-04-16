#!/usr/bin/env python3
"""
Prepare distribution ZIP file for HubAccelerator. 
The following parameters may be specified (use csvPrepare.py -h for help):

--role-arn ROLE_ARN 
--source-directory SOURCE_DIRECTORY
--bucket BUCKET
--folder FOLDER

REVISIONS:
* Make it work in GovCloud
"""
import argparse
import zipfile
import sys
import os
import re
import time
import logging
import csvObjects as csvo

_DEFAULT_LOGGING_LEVEL = logging.INFO
""" Default logging level """

# Set up logging
logging.basicConfig(level=_DEFAULT_LOGGING_LEVEL)

# Retrieve the logging instance
_LOGGER = logging.getLogger()
_LOGGER.setLevel(_DEFAULT_LOGGING_LEVEL)
""" Initialized logging RootLogger instance """

if __name__ == "__main__":
    """
    Main body is invoked if this is a command 
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-arn", required=False, 
        dest="roleArn", help="The ARN of an assumable role")
    parser.add_argument("--source-directory", required=True, 
        dest="sourceDirectory", help="CSV source directory")
    parser.add_argument("--bucket", required=False, 
        help="S3 bucket for storing code")
    parser.add_argument("--folder", required=False, 
        help="Code folder in S3 bucket")
    parser.add_argument("--primary-region", required=True,
        dest="region", help="Region for SSM & S3 operations"),

    arguments = parser.parse_args()

    # Get SSM client 
    ssmActor = csvo.SsmActor(
        role=arguments.roleArn, 
        region=arguments.region
    )

    # Set up for S3 operations using SSM parameters if necessary
    bucket = arguments.bucket if arguments.bucket \
        else getattr(ssmActor, "/csvManager/bucket", None)
    folder = arguments.folder if arguments.folder \
        else getattr(ssmActor, "/csvManager/folder/code", None)

    # Client for S3 operations
    s3Actor = csvo.S3Actor(
        role=arguments.roleArn, 
        bucket=bucket, 
        folder=folder, 
        region=arguments.region
    )

    # Name of zip file to contain source code
    pattern = re.compile(r'\.py$|\.yaml$|\.doc[x]*$')
    directory = arguments.sourceDirectory
    filename = "HubAcceleratorForSecurityHub-" + time.strftime("%Y%m%d-%H%M%S") + ".zip"
    inputFile = directory + "/" + filename

    # Build zip file
    with zipfile.ZipFile(inputFile, "w") as archive:
        for file in filter(pattern.search, os.listdir(directory)):
            archive.write(file)

    # This is where the source code zip file will go in S3
    outputObject = folder + "/" + filename

    # Perform the PUT operation
    s3Actor.put(inputFile=inputFile, outputObject=outputObject)

    # Set the name of the current code archive (zip file)
    ssmActor.putValue("/csvManager/object/codeArchive", 
        "HubAccelerator Code Archive", outputObject)

    _LOGGER.info("(r) IMPORTANT! Provide the following value " + \
        "for the \"code archive S3 key\" parameter in the " + \
        "CsvExporter stack: %s\n" % outputObject)
