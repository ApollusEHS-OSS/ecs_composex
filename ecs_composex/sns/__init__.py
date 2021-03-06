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

from ecs_composex.sns.sns_params import RES_KEY
from ecs_composex.common.stacks import ComposeXStack
from ecs_composex.common import load_composex_file, keyisset, LOG
from ecs_composex.common.ecs_composex import XFILE_DEST
from ecs_composex.sns.sns_templates import generate_sns_templates
from ecs_composex.sqs.sqs_params import RES_KEY as SQS_KEY


def create_sns_template(**kwargs):
    """
    Function to create SNS templates as part of ECS ComposeX.
    :param dict kwargs: unordered arguments
    :return: SNS root template
    :rtype: troposphere.Template
    """
    content = load_composex_file(kwargs[XFILE_DEST])
    if keyisset(RES_KEY, content):
        LOG.debug(f"Processing {RES_KEY} package")
        return generate_sns_templates(content, **kwargs)


class XResource(ComposeXStack):
    """
    Class to handle SQS Root stack related actions
    """

    def handle_sqs(self, root_template, sqs_root_stack):
        """
        Function to handle the SQS configuration to allow SNS to send messages to queues.
        """

    def add_xdependencies(self, root_template, content):
        """
        Method to add a dependencies from other X-Resources
        :param troposphere.Template root_template: The ComposeX Root template
        :param dict content: the compose file content
        """
        resources = root_template.resources
        sqs_res = SQS_KEY.strip("x-") if SQS_KEY.startswith("x-") else SQS_KEY
        if SQS_KEY in content and sqs_res in resources:
            self.DependsOn.append(sqs_res)
            self.handle_sqs(root_template, resources[sqs_res])
