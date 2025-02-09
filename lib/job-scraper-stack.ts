import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as nag from 'cdk-nag';
import { Construct } from 'constructs';
import { PythonLambdaLayer } from './python-lambda-layer-construct';


export interface Props extends cdk.StackProps {
  mainSearchTerm: string;
  openAiApiKey: string;
  searchTerms: string[];
  snsSubscribers: string;
}

export class JobScraperStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id, props);

    // SNS Topic for notifications
    const topic = new sns.Topic(this, 'JobScraperAlerts', {
      displayName: 'JobScraper Job Alerts',
    });

    // Subscribe an email to the SNS Topic
    // Copy & paste the link into the browser not from the email, see here:
    // https://repost.aws/knowledge-center/prevent-unsubscribe-all-sns-topic
    const snsSubscribersArray = props.snsSubscribers.split(',');
    for (const subscriber of snsSubscribersArray) {
      topic.addSubscription(new subscriptions.EmailSubscription(subscriber.trim()));
    }

    const layers:lambda.LayerVersion[] = !process.env.DISABLE_LAMBDA_LAYERS ? [
      new PythonLambdaLayer(this, 'PythonLambdaLayer', {
        arch: 'manylinux2014_aarch64',
        folderPath: 'lambda_layer/python',
        description: 'Python lambda layer for Web Scrapping',
      }),
    ] : [];

    // Lambda Function to scrape websites
    const scraperLambda = new lambda.Function(this, 'ScraperLambda', {
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'scraper.lambda_handler',
      code: lambda.Code.fromAsset('lambda'),
      timeout: cdk.Duration.seconds(30),
      environment: {
        SNS_TOPIC_ARN: topic.topicArn,
        // Combine the search terms into a single comma-separated string.
        SEARCH_TERMS: this.serializeSearchTerms(props.searchTerms),
        MAIN_SEARCH_TERM: props.mainSearchTerm,
        OPENAI_API_KEY: props.openAiApiKey,
      },
      layers: [...layers],
    });

    // Grant Lambda permission to publish to SNS
    topic.grantPublish(scraperLambda);

    // Schedule Lambda to run daily at 9 AM UTC
    new events.Rule(this, 'DailyScraperSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '9' }),
      targets: [new targets.LambdaFunction(scraperLambda)],
    });

    nag.NagSuppressions.addResourceSuppressions(topic, [
      {
        id: 'AwsSolutions-SNS3',
        reason: 'Suppress AwsSolutions-SNS3, called only from Lambda for now',
      },
    ]);

    nag.NagSuppressions.addResourceSuppressions(scraperLambda.role!, [
      {
        id: 'AwsSolutions-IAM4',
        reason: 'Suppress AwsSolutions-IAM4 approved managed policies',
        appliesTo: [
          {
            regex: '/(.*)(AWSLambdaBasicExecutionRole)(.*)$/g',
          },
        ],
      },
    ]);

  }

  serializeSearchTerms(searchTerms: string[]): string {
    return searchTerms.join(',');
  }
}
