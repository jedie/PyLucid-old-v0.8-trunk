# -*- coding: utf-8 -*-

"""
    PyLucid find and replace
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Find/Replace in all page/template/stylesheet content.

    Known bugs:
        SQLite doesn’t support case-sensitive LIKE statements, we add some
        "SQLite work-a-round" for this. Otherwise we would get a empty result
        list. Note: The real replace operation always works case-sensitive.
        See also: http://www.djangoproject.com/documentation/db-api/#contains

    Last commit info:
    ~~~~~~~~~
    $LastChangedDate$
    $Rev$
    $Author$

    :copyleft: 2008 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v2 or above, see LICENSE for more details
"""

__version__= "$Rev$"

import time

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from PyLucid.system.BasePlugin import PyLucidBasePlugin
from PyLucid.models import Page, Plugin, Template, Style
from PyLucid.tools.Diff import diff_lines
from PyLucid.tools.utils import escape


# for FindReplaceForm ChoiceField
TYPES = (
    ("pages", "pages"),
    ("templates", "templates"),
    ("stylesheets", "stylesheets"),
)


# We used preferences values in a newform. We need these values here.
preferences = Plugin.objects.get_preferences(__file__)

min_term_len = preferences["min_term_len"]
max_term_len = preferences["max_term_len"]


class FindReplaceForm(forms.Form):
    # TODO: min und max should be saved in the prefereces.
    find_string = forms.CharField(
        min_length = min_term_len, max_length = max_term_len,
    )
    replace_string = forms.CharField(
        min_length = min_term_len, max_length = max_term_len,
    )
    type = forms.ChoiceField(
        choices=TYPES,
        help_text = _("Please select the content type for the operation.")
    )
    simulate = forms.BooleanField(
        initial = True, required = False,
        help_text = _("Don't replace anything.")

    )


class find_and_replace(PyLucidBasePlugin):

    def find_and_replace(self):
        context = {}
        if self.request.method == 'POST':
            form = FindReplaceForm(self.request.POST)
            if form.is_valid():
                start_time = time.time()
                results, total_changes = self.do(**form.cleaned_data)
                context = {
                    "results": results,
                    "total_changes": total_changes,
                    "duration": time.time() - start_time,
                }
        else:
            form = FindReplaceForm()

        context["form"] = form
        self._render_template("find_and_replace", context)#, debug=True)


    def do(self, find_string, replace_string, type, simulate):
        """
        Do the find/replace action.
        Returns a result list with diff information.
        """
        def nothing_found():
            # We used this two times
            self.page_msg(
                "No %s contains the string '%s'" % (type, find_string)
            )
            return None, None

        if type == "pages":
            model_object = Page
        elif type == "templates":
            model_object = Template
        elif type == "stylesheets":
            model_object = Style
        else:
            self.page_msg.red("Wrong type!")
            return None, None

        items = model_object.objects.all().filter(
            content__contains=find_string
        )
        if len(items) == 0:
            return nothing_found()

        total_changes = 0
        results = []
        changed_items = []
        for item in items:
            old_content = item.content

            changes = old_content.count(find_string)
            if changes == 0:
                # SQlite work-a-round for the
                continue

            total_changes += changes

            new_content = old_content.replace(find_string, replace_string)
            if not simulate:
                # Save the find/replace result
                item.content = new_content
                item.save()
                changed_items.append(item.name)

            diff = diff_lines(old_content, new_content)
            diff = escape(diff)
            diff = mark_safe(diff)

            results.append({
                "item": item,
                "changes": changes,
                "diff": diff,
            })

        if total_changes == 0:
            # SQLite work-a-round
            return nothing_found()

        if not simulate:
            self.page_msg.green("Changed %s:" % type)
            self.page_msg.green(", ".join(changed_items))

        return results, total_changes




