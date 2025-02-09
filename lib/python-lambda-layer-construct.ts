// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

interface Props {
  arch: string;
  description: string;
  folderPath: string;
}

export class PythonLambdaLayer extends lambda.LayerVersion {
  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id, {
      code: lambda.Code.fromAsset(props.folderPath, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          command: [
            'bash', '-c',
            // create a new virtualenv for python to use
            // so that it isn't using root
            'python -m venv /tmp/venv && ' +
            // Create a new location for the pip cache
            'mkdir /tmp/pip-cache &&' +
            'chmod -R 777 /tmp/pip-cache &&' +
            'export PIP_CACHE_DIR=/tmp/pip-cache &&' +
            'export PATH="/tmp/venv/bin:$PATH" &&' +
            `pip install --platform ${props.arch} --only-binary=:all: -r requirements.txt -t /asset-output/python`,
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12, lambda.Runtime.PYTHON_3_13],
      description: props.description,
    });
  }
}