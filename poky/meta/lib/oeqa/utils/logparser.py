#!/usr/bin/env python

import sys
import os
import re

# A parser that can be used to identify weather a line is a test result or a section statement.
class PtestParser(object):
    def __init__(self):
        self.results = {}
        self.sections = {}

    def parse(self, logfile):
        test_regex = {}
        test_regex['PASSED'] = re.compile(r"^PASS:(.+)")
        test_regex['FAILED'] = re.compile(r"^FAIL:(.+)")
        test_regex['SKIPPED'] = re.compile(r"^SKIP:(.+)")

        section_regex = {}
        section_regex['begin'] = re.compile(r"^BEGIN: .*/(.+)/ptest")
        section_regex['end'] = re.compile(r"^END: .*/(.+)/ptest")
        section_regex['duration'] = re.compile(r"^DURATION: (.+)")
        section_regex['exitcode'] = re.compile(r"^ERROR: Exit status is (.+)")
        section_regex['timeout'] = re.compile(r"^TIMEOUT: .*/(.+)/ptest")

        def newsection():
            return { 'name': "No-section", 'log': "" }

        current_section = newsection()

        with open(logfile, errors='replace') as f:
            for line in f:
                result = section_regex['begin'].search(line)
                if result:
                    current_section['name'] = result.group(1)
                    continue

                result = section_regex['end'].search(line)
                if result:
                    if current_section['name'] != result.group(1):
                        bb.warn("Ptest END log section mismatch %s vs. %s" % (current_section['name'], result.group(1)))
                    if current_section['name'] in self.sections:
                        bb.warn("Ptest duplicate section for %s" % (current_section['name']))
                    self.sections[current_section['name']] = current_section
                    del self.sections[current_section['name']]['name']
                    current_section = newsection()
                    continue

                result = section_regex['timeout'].search(line)
                if result:
                    if current_section['name'] != result.group(1):
                        bb.warn("Ptest TIMEOUT log section mismatch %s vs. %s" % (current_section['name'], result.group(1)))
                    current_section['timeout'] = True
                    continue

                for t in ['duration', 'exitcode']:
                    result = section_regex[t].search(line)
                    if result:
                        current_section[t] = result.group(1)
                        continue

                current_section['log'] = current_section['log'] + line 

                for t in test_regex:
                    result = test_regex[t].search(line)
                    if result:
                        if current_section['name'] not in self.results:
                            self.results[current_section['name']] = {}
                        self.results[current_section['name']][result.group(1)] = t

        return self.results, self.sections

    # Log the results as files. The file name is the section name and the contents are the tests in that section.
    def results_as_files(self, target_dir):
        if not os.path.exists(target_dir):
            raise Exception("Target directory does not exist: %s" % target_dir)

        for section in self.results:
            prefix = 'No-section'
            if section:
                prefix = section
            section_file = os.path.join(target_dir, prefix)
            # purge the file contents if it exists
            with open(section_file, 'w') as f:
                for test_name in sorted(self.results[section]):
                    status = self.results[section][test_name]
                    f.write(status + ": " + test_name + "\n")

