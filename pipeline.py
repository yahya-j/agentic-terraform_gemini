# ==============================================================================
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# ==============================================================================

import logging

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, steps=[]):
        """
        Initialise the pipeline with steps to execute

        Args:
            steps: List of steps to execute
        """
        self.steps = steps

    def result(self, messages):
        """
        Concat last messages and calculate IaC output

        Args:
            messages: Current messages in the context
        """

        result = []
        for message in messages[::-1]:
            if message["role"] != "assistant":
                break

            result.insert(0, message["content"])

        return "".join(result)

    def run(self, user_prompt):
        """
        Run the pipeline based on steps defined and user_prompt provided

        Args:
            user_prompt:

        Returns:
            LLM result based on user_prompt
        """

        messages = []
        meta = {}

        while True:
            retried = False

            for step in self.steps:
                (messages, needs_retry, step_meta) = step.get_messages(
                    messages, user_prompt, meta.get(step.__class__.__name__, {})
                )

                meta[step.__class__.__name__] = step_meta

                if needs_retry:
                    retried = True
                    break

            if not retried:
                return self.result(messages)
