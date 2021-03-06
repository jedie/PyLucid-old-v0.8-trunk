# -*- coding: utf-8 -*-

"""
    PyLucid Show Internals - System Info
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Last commit info:
    ~~~~~~~~~~~~~~~~~
    $LastChangedDate$
    $Rev$
    $Author$

    :copyleft: 2005-2008 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

__version__= "$Rev$"

import os, pprint

from django.views.debug import get_safe_settings

from PyLucid.tools.utils import escape
from PyLucid.system.BasePlugin import PyLucidBasePlugin

#______________________________________________________________________________
class PyLucidInfo(PyLucidBasePlugin):
    """
    information around PyLucid
    """
    def display_all(self):
        self.response.write("<hr>")
        self.PyLucid_info()
        self.pygments_info()
        self.envion_info()


    def PyLucid_info(self):
        self.response.write("<h3>PyLucid environ information</h3>")

        self.response.write('<fieldset id="system_info">')
        self.response.write(
            '<legend>'
            '<a href="http://www.pylucid.org/_goto/62/self-URLs/">'
            'PyLucid["URLs"]</a>:'
            '</legend>'
        )
        self.response.write("<pre>")

        data = [(len(v), k, v) for k,v in self.URLs.items()]

        max_len = max([len(k) for k in self.URLs])
        line = "%%%ss: '%%s'\n" % max_len

        for _,k,v in sorted(data):
            self.response.write(line % (k,v))

        self.response.write("</pre>")
        self.response.write("</fieldset>")
        
    
    def pygments_info(self):
        self.response.write("<h3>Pygments information</h3>")
        self.response.write("<pre>")
        
        from PyLucid.system import hightlighter
        
        if hightlighter.PYGMENTS_AVAILABLE == False:
            self.response.write("pygments is not available!\n")
            self.response.write(
                "The import error was: %s\n" % hightlighter.import_error
            )
            self.response.write(
                'PyPi url http://pypi.python.org/pypi/Pygments\n'
            )
        else:
            self.response.write("pygments is available!\n")
            pygments = hightlighter.pygments
            self.response.write(
                "module: %r\n" % getattr(pygments, "__file__", "?")
            )
            self.response.write(
                "version: %r\n" % getattr(pygments, "__version__", "?")
            )
        
        self.response.write("</pre>")


    def envion_info(self):
        self.response.write("<h3>OS-Enviroment:</h3>")
        self.response.write('<dl id="environment">')
        keys = os.environ.keys()
        keys.sort()
        for key in keys:
            value = os.environ[key]
            self.response.write("<dt>%s</dt>" % key)
            self.response.write("<dd>%s</dd>" % value)
        self.response.write("</dl>")


#______________________________________________________________________________
class DjangoInfo(PyLucidBasePlugin):
    """
    information around PyLucid
    """
    def display_all(self):
        self.response.write("<hr>")
        self.response.write("<h3>Django environ information</h3>")
        self.apps_models()
        self.django_info()
        self.header_info()

    def apps_models(self):
        """
        List of all installed apps and his models.
        """
        from django.db.models import get_apps, get_models

        self.response.write('<fieldset id="system_info">')
        self.response.write(
            '<legend>apps / models list</legend>'
        )
        self.response.write("<ul>")

        apps_info = []
        for app in get_apps():
            self.response.write(
                "<li><strong>%s</strong></li>" % app.__name__
            )
            self.response.write("<ul>")
            for model in get_models(app):
                model_name = model._meta.object_name
                self.response.write(
                    "<li>%s</li>" % model_name
                )
            self.response.write("</ul>")

        self.response.write("</ul>")
        self.response.write("</fieldset>")

    def django_info(self):
        from django.db import connection, backend

        self.response.write('<fieldset id="system_info">')
        self.response.write(
            '<legend>database info</legend>'
        )
       
        #----------------------------------------------------------------------

        self.response.write("<h4>used dbapi:</h4>")
        self.response.write("<pre>")
        self.response.write("name: %s\n" % backend.Database.__name__)
        self.response.write("module: %s\n" % backend.Database.__file__)
        self.response.write(
            "version: %s\n" % getattr(backend.Database, "version", "?")
        )
        self.response.write("</pre>")
        
        #----------------------------------------------------------------------

        self.response.write("<h4>table names:</h4>")
        self.response.write("<pre>")
        tables = connection.introspection.table_names()
        self.response.write("\n".join(sorted(tables)))
        self.response.write("</pre>")
        
        #----------------------------------------------------------------------

        self.response.write("<h4>django table names:</h4>")
        self.response.write("<pre>")
        django_tables = connection.introspection.django_table_names()
        self.response.write("\n".join(sorted(django_tables)))
        self.response.write("</pre>")

        self.response.write("</fieldset>")

    def header_info(self):
        self.response.write('<fieldset id="system_info">')
        self.response.write(
            '<legend>request.META</legend>'
        )
        self.response.write("<pre>")
        self.response.write(pprint.pformat(self.request.META))
        self.response.write("</pre>")

        self.response.write("</fieldset>")


#______________________________________________________________________________
class SettingsInfo(PyLucidBasePlugin):
    """
    display current used 'settings.py'
    """
    def display_all(self):
        self.context["settings_info"] = self.settings_info()
        
        self._render_template(
            internal_page_name="settings_info",
            context=self.context,
            #debug=True,
        )

    def settings_info(self):
        """
        display current used 'settings.py'
        """
        context = []
        
        safe_settings = get_safe_settings()
        for key, value in safe_settings.iteritems():
            value = pprint.pformat(value)
            value = escape(value)
            context.append({
                "attrname": key,
                "value": value,
            })
        
        context.sort()
        
        return context            

