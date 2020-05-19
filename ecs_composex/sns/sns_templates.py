﻿#  -*- coding: utf-8 -*-
#   ECS ComposeX <https://github.com/lambda-my-aws/ecs_composex>
#   Copyright (C) 2020  John Mille <john@lambda-my-aws.io>
#  #
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#  #
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#  #
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Module to add topics and subscriptions to the SNS stack
"""

from troposphere.sns import Topic, Subscription
from ecs_composex.common import LOG, keyisset, build_template, NONALPHANUM
from ecs_composex.common.stacks import ComposeXStack
from ecs_composex.common.outputs import define_import
from ecs_composex.sqs.sqs_params import SQS_ARN_T, RES_KEY as SQS_KEY
from ecs_composex.sns.sns_params import RES_KEY

TOPICS_KEY = "Topics"
SUBSCRIPTIONS_KEY = "Subscriptions"
TOPICS_STACK_NAME = "topics"


def check_queue_exists(queue_name, content):
    """
    Function to check

    :param str queue_name: Name of the queue defined in the subscription
    :param dict content: docker compose file content
    :return:
    """
    if keyisset(SQS_KEY, content):
        if not queue_name.startswith("arn:") and keyisset(queue_name, content[SQS_KEY]):
            return True
        elif queue_name.startswith("arn"):
            LOG.warning(
                f"Queue {queue_name} added as target, but not validated whether it exists"
            )
            return True
        else:
            LOG.error(f"Queue {queue_name} not defined in the {SQS_KEY} section")
            return False


def set_sqs_topic(subscription, content):
    """
    Function to set permissions and import for SQS subscription
    :return:
    """
    if not subscription["Endpoint"].startswith("arn:"):
        assert check_queue_exists(subscription["Endpoint"], content)
    endpoint = (
        define_import(subscription["Endpoint"], SQS_ARN_T)
        if not subscription["Endpoint"].startswith("arn:")
        else subscription["Endpoint"]
    )

    return Subscription(Protocol="sqs", Endpoint=endpoint)


def define_topic_subscriptions(subscriptions, content):
    """
    Function to define an SNS topic subscriptions

    :param list subscriptions: list of subscriptions as defined in the docker compose file
    :param troposphere.sns.Topic topic: the SNS topic to add the subscriptions to
    :param dict content: docker compose file content
    :return:
    """
    required_keys = ["Endpoint", "Protocol"]
    subscriptions_objs = []
    for sub in subscriptions:
        if not any(key in sub for key in required_keys):
            raise AttributeError(
                "Required attributes for Subscription are",
                required_keys,
                "Provided",
                sub.keys(),
            )
        if sub["Protocol"] == "sqs" or sub["Protocol"] == "SQS":
            subscriptions_objs.append(set_sqs_topic(sub, content))
        else:
            subscriptions_objs.append(sub)
    return subscriptions_objs


def define_topic(topic_name, topic, content):
    """
    Function that builds the SNS topic template from Dockerfile Properties
    """
    properties = topic["Properties"] if keyisset("Properties", topic) else {}
    topic = Topic(NONALPHANUM.sub("", topic_name))
    if keyisset(SUBSCRIPTIONS_KEY, properties):
        subscriptions = define_topic_subscriptions(
            properties[SUBSCRIPTIONS_KEY], content
        )
        setattr(topic, "Subscription", subscriptions)

    for key in properties.keys():
        if type(properties[key]) != list:
            setattr(topic, key, properties[key])
    return topic


def add_topics_to_template(template, topics, content):
    """
    Function to interate over the topics and add them to the CFN Template

    :param troposphere.Template template:
    :param dict topics:
    :param dict content: Content of the compose file
    """
    for topic_name in topics:
        template.add_resource(
            define_topic(topic_name, content[RES_KEY][TOPICS_KEY][topic_name], content)
        )


def add_sns_topics(root_template, content, res_count, count=170, **kwargs):
    """
    Function to add SNS topics to the root template

    :param int count: quantity of resources that should trigger the split into nested stacks
    :param root_template:
    :param content:
    :param int res_count: Number of resources created related to SNS
    :param kwargs:
    :return:
    """
    if res_count > count:
        LOG.info(
            f"There are more than {count} resources to handle for SNS. Splitting into nested stacks"
        )
        template = build_template("Root stack for SNS topics")
        add_topics_to_template(template, content[RES_KEY][TOPICS_KEY], content)
        root_template.add_resource(
            ComposeXStack(title=TOPICS_STACK_NAME, stack_template=template, **kwargs)
        )
    else:
        add_topics_to_template(root_template, content[RES_KEY][TOPICS_KEY], content)


def define_resources(res_content):
    """
    Function to determine how many resources are going to be created.
    :return:
    """
    res_count = 0
    if keyisset(TOPICS_KEY, res_content):
        for topic in res_content[TOPICS_KEY]:
            res_count += 1
            if keyisset("Subscription", topic):
                res_count += len(topic["Subscription"])
    if keyisset(SUBSCRIPTIONS_KEY, res_content):
        res_count += len(res_content[SUBSCRIPTIONS_KEY])
    return res_count


def generate_sns_templates(content, **kwargs):
    """
    Entrypoint function to generate the SNS topics templates
    :param content:
    :param kwargs:
    :return:
    """
    allowed_keys = [TOPICS_KEY, SUBSCRIPTIONS_KEY]
    res_content = content[RES_KEY]
    if not set(res_content).issubset(allowed_keys):
        raise KeyError(
            "SNS Only supports two types of resources",
            allowed_keys,
            "provided",
            res_content.keys(),
        )
    root_template = build_template("SNS Root Template")
    res_count = define_resources(res_content)
    if keyisset(TOPICS_KEY, res_content):
        add_sns_topics(root_template, content, res_count, **kwargs)
    if keyisset(SUBSCRIPTIONS_KEY, res_content):
        pass
    return root_template