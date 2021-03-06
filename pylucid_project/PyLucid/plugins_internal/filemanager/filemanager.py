# -*- coding: utf-8 -*-

"""
    PyLucid media file manager
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    We have two kinds of forms: POST actions and GET actions
    POST actions are:
        - filemanager.action_mkdir()
        - filemanager.action_fileupload()
        - filemanager.action_rmdir()
        - filemanager.action_deletefile()
    GET actions are:
        - filemanager.edit() (Edit a text file)

    POST action note:
        The POST actions used a hidden field named "action" for easy differ
        the the current action in the POST data. See below the constants.
    GET action notes:
        - The GET forms should not insert a field named "action"!
        - After a finished GET method, it should display the filelist().


    restrictions:
        - Only tested under linux!

    TODO:
        - should use posixpath for every URL stuff.
        - deny editing of binary files (how? ext whitelist or using file?)
        - insert the basepath selection into the filelist view.
        - find a way to reduce the redundance.
        - Write a unitest for the plugin and verify the "bad-char-things" in
            path/post variables.
        - Fixe some unicode problems:
            e.g.: upload a file with a non ascii content
            use sys.getfilesystemencoding() ?
        - Check the Plugin under windows - very low priority :)

    Last commit info:
    ~~~~~~~~~
    $LastChangedDate$
    $Rev$
    $Author$

    :copyleft: 2007-2008 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v2 or above, see LICENSE for more details
"""

__version__= "$Rev: $"

import os, cgi, sys, stat, dircache, time
from datetime import datetime

from django import forms
from django.conf import settings
from django.http import HttpResponse
from django.forms import ValidationError
from django.utils.translation import ugettext as _

from PyLucid.system.BaseFilesystemPlugin import FilesystemPlugin
from PyLucid.forms.filesystem import FilenameField, DirnameField

#______________________________________________________________________________
# We use more than one html form in a filelist page. So we need some unique
# action values for a easier distinguish the POST data.
ACTION_RMDIR = "0"
ACTION_MKDIR = "1"
ACTION_FILEUPLOAD = "2"
ACTION_DELETEFILE = "3"

#______________________________________________________________________________

def make_dirlist(path, result=[]):
    """
    Helper function for building a directory link line.
    used in filemanager.make_dir_links()

    >>> make_dirlist("/data/one/two")
    [('data/one/two', 'two'), ('data/one', 'one'), ('data', 'data')]
    """
    path = path.strip("/")

    head, tail = os.path.split(path)
    result.append((path, tail))

    if head:
        # go recusive deeper
        return make_dirlist(head, result)
    else:
        result.reverse()
        return result

#______________________________________________________________________________

class EditFileForm(forms.Form):
    """ Edit a text file form """
    filename = FilenameField(
        help_text=_(
            u"Change the filename,"
            " if you want to save the content into a new file."
        )
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs = {'cols': '80', 'rows': '25'})
    )


#______________________________________________________________________________

class ActionField(forms.CharField):
    """
    A spezial HiddenInput field for the action string.
    The action string is set in the forms.Form class and must be the same in
    the POST data, otherwise the form is not valid.
    """
    def __init__(self, action):
        self.action = action
        max_length = min_length = len(action)
        super(ActionField, self).__init__(
            max_length=max_length, min_length=min_length,
            required=True, initial=action,
            widget=forms.HiddenInput,
        )

    def clean(self, value):
        super(ActionField, self).clean(value)
        if value != self.action:
            raise ValidationError(_(u"Wrong action!"))
        return value

#______________________________________________________________________________

class CreateDirForm(forms.Form):
    """
    Form for creating a new directory
    ToDo: add a choice field for create a file or a directory action
    """
    action = ActionField(ACTION_MKDIR)
    dirname = DirnameField(
        help_text="Create a new directory into the current directory."
    )


class UploadFileForm(forms.Form):
    """ Form to upload a new file """
    action = ActionField(ACTION_FILEUPLOAD)
    ufile = forms.FileField(
        label="filename",
        help_text="Upload a new file into the current directory."
    )

class RmDirForm(forms.Form):
    """
    Delete a directory.
    """
    action = ActionField(ACTION_RMDIR)
    item_name = DirnameField(
        help_text="Create a new directory into the current directory."
    )

class DeleteFileForm(forms.Form):
    """
    Delete one file.
    """
    action = ActionField(ACTION_DELETEFILE)
    item_name = FilenameField()




#______________________________________________________________________________

class filemanager(FilesystemPlugin):
    """
    The PyLucid plugin class.
    """
    def get_filelist(self):
        """
        Returns all items in the given directory.
        -rel_dir is relative to ABS_PATH
        -the listing is sorted and the first items are the directories.
        """
        files = []

        if self.path["rel_path"] == "":
            # current dir is the media root
            dirs=[]
        else:
            # Add the ".." dir item
            updir = os.path.split(self.path["rel_path"])[0]
            dirs = [{
                "name": "..",
                "link": self.URLs.methodLink(
                    method_name="filelist", args=(self.path["base_key"], updir)
                ),
                "is_dir": True,
                "deletable": False,
                "dont_display_size": True,
            }]

        link_prefix = self.URLs.methodLink(
            method_name="filelist", args=self.path["url_path"]
        )

        for item in sorted(os.listdir(self.path["abs_path"])):
            if item.startswith("."):
                # skip hidden files or directories
                continue

            abs_item_path = os.path.join(self.path["abs_path"], item)
            statinfo = os.stat(abs_item_path)

            if stat.S_ISDIR(statinfo.st_mode):
                # Is a directory
                is_dir = True
                link = os.path.join(link_prefix, item) + "/"
                size = len(dircache.listdir(
                    os.path.join(self.path["abs_path"], item)
                ))
            else:
                is_dir = False
                link = self.path.get_abs_link(item)
                size = statinfo.st_size

            mtime = statinfo.st_mtime
            localtime = time.gmtime(mtime)
            localdatetime = datetime(*localtime[:6])

            item_dict={
                "name": item,
                "link": link,
                "is_dir": is_dir,
                "title": abs_item_path,
                "time": localdatetime,
                "size": size,
                "mode": statinfo.st_mode,
                "uid": statinfo.st_uid,
                "gid": statinfo.st_gid,
                "deletable": True,
            }
            if is_dir:
                dirs.append(item_dict)
            else:
                files.append(item_dict)

        # return the merged list of direcories and files together
        dir_list = dirs + files
        return dir_list


    def make_dir_links(self):
        """
        Build the context for the path link line.
        Use the function make_dirlist().
        """
        # start with the first base_path entry:
        dir_links = [{
            "name": self.path["base_fs_path"], # use only the short relative path
            "title": self.path["abs_path"],
            "link": self.URLs.methodLink(
                method_name="filelist", args=self.path["base_key"]
            ),
        }]
        if self.path["rel_path"] != "":
            # Not in the root
            dirlist = make_dirlist(self.path["rel_path"], [])
            for path, name in dirlist:
                # append every dir "steps"
                dir_links.append({
                    "name": name,
                    "title": os.path.join(self.path["base_fs_path"], path),
                    "link": self.URLs.methodLink(
                        method_name="filelist",
                        args=(self.path["base_key"], path)
                    ),
                })

        return dir_links

    #--------------------------------------------------------------------------
    # html GET actions:

    def edit(self, path_info):
        """
        Edit a text file.
        """
        self.path.new_filename_path(path_info, must_exist=True)
        #self.path.debug()

        try:
            f = file(self.path["abs_file_path"], "r")
            content = f.read()
            f.close()
            content = content.decode(settings.FILE_CHARSET)
        except Exception, e:
            self.page_msg.red("Error, reading file:", e)
            return

        if self.request.method != 'POST':
            form = EditFileForm({
                "content": content,
                "filename": self.path["filename"],
            })
        else: # POST
            #self.page_msg(self.request.POST)
            form = EditFileForm(self.request.POST)
            if form.is_valid():
                filename = form.cleaned_data["filename"]
                content = form.cleaned_data["content"]
                abs_file_path = os.path.join(self.path["abs_path"], filename)
                try:
                    content = content.encode(settings.FILE_CHARSET)
                    f = file(abs_file_path, "w")
                    f.write(content)
                    f.close()
                except Exception, e:
                    self.page_msg.red("Error, writing file:", e)
                else:
                    self.page_msg.green(
                        "New content saved into '%s'." % filename
                    )
                    # Display the filelist
                    return self.filelist(self.path["url_path"])

        # Don't include the filename in methodLink-args, it always append a
        # slash!
        form_link = self.URLs.methodLink(
            method_name="edit", args=self.path["url_path"]
        )
        form_link += self.path["filename"]

        file_path = self.path.get_abs_link()

        # Change the global page title:
        self.context["PAGE"].title = _("Edit file - %s" % file_path)

        context = {
            "form_link": form_link,
            "url_abort": self.URLs.methodLink(
                method_name="filelist", args=self.path["url_path"]
            ),
            "file_path": file_path,
            "filename": self.path["filename"],
            "form": form,
            "charset": settings.FILE_CHARSET,
        }
        self._render_template("edit_file", context)#, debug=True)

    #--------------------------------------------------------------------------
    # html POST actions:

    def action_mkdir(self, dirname):
        """
        create a new directory
        """
        abs_new_path = os.path.join(self.path["abs_path"], dirname)
        try:
            os.mkdir(abs_new_path)
        except Exception, e:
            self.page_msg.red("Can't create '%s': %s" % (dirname, e))
        else:
            self.page_msg.green("'%s' creaded successfull." % dirname)


    def action_fileupload(self, ufile):
        """
        save a uploaded file.
        """
        filename = ufile.name
        abs_fs_path = os.path.join(self.path["abs_path"], filename)
        try:
            f = file(abs_fs_path,'wb') # if it exists, overwrite

            for chunk in ufile.chunks():
                f.write(chunk)

            f.close()
        except Exception, e:
            self.page_msg.red("Can't write file: '%s'" % e)
            return

        statinfo = os.stat(abs_fs_path)
        real_filesize = statinfo.st_size

        if real_filesize == ufile.size:
            self.page_msg.green(
                "File '%s' written successfull. (%s Bytes)" % (
                    filename, real_filesize
                )
            )
        else: # Should never appear
            self.page_msg.red(
                "Error writing file '%s'."
                " Filesize is different:"
                " Should be %s Bytes, but is %s Bytes" % (
                    ufile.file_size, real_filesize
                )
            )


    def action_rmdir(self, dirname):
        """ delete a directory """
        abs_fs_path = os.path.join(self.path["abs_path"], dirname)
        try:
            os.rmdir(abs_fs_path)
        except Exception, e:
            self.page_msg.red("Can't delete '%s': %s" % (dirname, e))
        else:
            self.page_msg.green("'%s' deleted successfull." % dirname)


    def action_deletefile(self, filename):
        """ delete a file """
        abs_fs_path = os.path.join(self.path["abs_path"], filename)
        try:
            os.remove(abs_fs_path)
        except Exception, e:
            self.page_msg.red("Can't delete '%s': %s" % (filename, e))
        else:
            self.page_msg.green("File '%s' deleted successfull." % filename)

    #--------------------------------------------------------------------------

    def userinfo(self, old_path=""):
        """
        Display some user information related to the filemanager functionality.
        """
        # Change the global page title:
        self.context["PAGE"].title = _(
            "Filemanager - Display some user information"
        )

        import pwd, grp

        uid = os.getuid()
        gid = os.getgid()

        pwd_info = pwd.getpwuid(os.getuid())
        grp_info = grp.getgrgid(os.getgid())

        context = {
            "filelist_link": self.URLs.methodLink(
                method_name="filelist", args=old_path
            ),
            "uid": uid,
            "gid": gid,
            "pwd_info": pwd_info,
            "grp_info": grp_info,
        }
#        self.page_msg(context)
        self._render_template("userinfo", context)#, debug=True)

    def select_basepath(self):
        """
        change the basepath, after send the form, we display the filelist
        """
        # Change the global page title:
        self.context["PAGE"].title = _("Filemanager - Change the basepath")
        
        context = {}

        path_key = self.basepath_form(context)
        if not path_key:
            self._render_template("select_basepath", context)#, debug=True)
        else:
            # POST with valide form data -> display the filelist
            self.filelist(path_key + u"/")            

    #--------------------------------------------------------------------------

    def filelist(self, path_info=None):
        """
        List dir and file. Some actions.
        rest: path to dir or file
        """        
        if not path_info:
            self.select_basepath()
            return

        # analyse and store the given GET path infomation
        self.path.new_dir_path(path_info, must_exist=True)
        #self.path.debug()

        # Change the global page title:
        path = os.path.join(self.path["base_fs_path"], self.path["rel_path"])
        self.context["PAGE"].title = _("File list - %s" % path)

        # We init all forms before we check the POST, because we only need
        # error information for the current action. Only the form for the
        # current action should be inited with self.request.POST!
        ufile_form = UploadFileForm()
        mkdir_form = CreateDirForm()

        if self.request.method == 'POST' and "action" in self.request.POST:
            #self.page_msg(self.request.POST)
            action = self.request.POST["action"]

            #------------------------------------------------------------------
            # action in the current directory:

            if action == ACTION_MKDIR:
                # Create a new directory
                mkdir_form = CreateDirForm(self.request.POST)
                if mkdir_form.is_valid():
                    dirname = mkdir_form.cleaned_data["dirname"]
                    self.action_mkdir(dirname)

            elif action == ACTION_FILEUPLOAD:
                # save a uploaded file
                ufile_form = UploadFileForm(
                    self.request.POST, self.request.FILES
                )
                if ufile_form.is_valid():
                    ufile = ufile_form.cleaned_data["ufile"]
                    self.action_fileupload(ufile)

            #------------------------------------------------------------------
            # action for one file/directory:

            elif action == ACTION_RMDIR:
                # delete a directory
                form = RmDirForm(self.request.POST)
                if form.is_valid():
                    dirname = form.cleaned_data["item_name"]
                    self.action_rmdir(dirname)

            elif action == ACTION_DELETEFILE:
                # delete a file
                form = DeleteFileForm(self.request.POST)
                if form.is_valid():
                    filename = form.cleaned_data["item_name"]
                    self.action_deletefile(filename)

        # build the directory+file list:
        dir_list = self.get_filelist()

        # Build the path link line:
        dir_links = self.make_dir_links()

        # if the current path is writeable?
        writeable = os.access(self.path["abs_path"], os.W_OK)

        context = {
#            "path": self.path,
            "post_url": self.URLs.methodLink(
                method_name="filelist", args=self.path["url_path"]
            ),

            "mkdir_form": mkdir_form,
            "ufile_form": ufile_form,

            "ACTION_RMDIR": ACTION_RMDIR,
            "ACTION_DELETEFILE": ACTION_DELETEFILE,

            "dir_links": dir_links,
            "writeable": writeable,
            "dir_list": dir_list,

            "userinfo_link": self.URLs.methodLink(
                method_name="userinfo", args=self.path["url_path"]
            ),
            "edit_link": self.URLs.methodLink(
                method_name="edit", args=self.path["url_path"]
            ),
            "change_basepath_link": self.URLs.methodLink(
                method_name="select_basepath"
            ),
        }
        #self.page_msg(context)
        self._render_template("filelist", context)#, debug=True)

# -----------------------------------------------------------------------------

class WrongDirectory(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class BadFilename(Exception):
    """ A not allowed character contain a filename """
    pass

class BadPath(Exception):
    """ A not allowed character contain a path """
    pass

