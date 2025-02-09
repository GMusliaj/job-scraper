#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as nag from 'cdk-nag';
import { JobScraperStack } from '../lib/job-scraper-stack';

const app = new cdk.App();
new JobScraperStack(app, 'JobScraperStack', {
  mainSearchTerm: process.env.MAIN_SEARCHTERM!,
  openAiApiKey: process.env.OPENAI_API_KEY!,
  searchTerms: ['Germany', 'Munich'],
  snsSubscribers: process.env.SNS_SUBSCRIBERS!,
});

cdk.Aspects.of(app).add(new nag.AwsSolutionsChecks({ verbose: false }));