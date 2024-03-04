# IMPETUS CT Indexer

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/IMIS-MIKI/impetus-ct-indexer/blob/main/LICENSE)

## Table of Contents
- [Background](#background)
- [Installation](#installation)
- [Usage](#usage)

## Background

This repository presents the IMPETUS CT Indexer, a project aimed at enhancing the metadata of CT imaging series within the Medical Data Integration Center (MeDIC). The goal is to improve findability, accessibility, interoperability, and reusability of clinical imaging data. We describe the implementation of the indexer, its integration with existing MeDIC architecture, and the results achieved.

![Overview](doc/ct-indexer.png)

## Installation
- Complete the env.template and save it as .env file
 - Run the indexer via Docker and pass the .env
`docker-compose up -d` 
- If you want to modify the indexer, you need to rebuild the Docker image
`docker build -t 'impetus-ct-indexer:<version>' `

## Usage

The indexer subscribes on to a Kafka topic and waits for tasks. A task has the following structure:
```json
{
    "identification" : {
		"mpi": "123456789",		
        "series": "1.2.3.4.5.6.7.8",
        "study": "1.2.3.4.5.6.7.8.9.10.11.12"
    },
    "s3-input" : {
        "s3-bucket" : "landing-ct-indexer",
        "s3-path" : "test.zip"
    }
}
```
The identification will be passed trough and is only used for the down-stream processing in the ElasticSearhc or the [FHIR export](https://github.com/IMIS-MIKI/impetus-ct-indexer-fhir).

