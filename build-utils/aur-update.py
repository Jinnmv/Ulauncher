#!/usr/bin/env python2

# Run in ArchLinux container

import os
import sys
import re
import urllib2
import json
from tempfile import mkdtemp
from subprocess import call


aur_repo = "ssh://aur@aur.archlinux.org/ulauncher.git"
project_path = os.path.abspath(os.sep.join((os.path.dirname(os.path.realpath(__file__)), '..')))


try:
    version = sys.argv[1]
except IndexError:
    print "ERROR: First argument should be version"
    sys.exit(1)

try:
    allow_unstable = os.environ['ALLOW_UNSTABLE'] in ('1', 'true')
except KeyError:
    print "Optional ALLOW_UNSTABLE is not set. Default to False"
    allow_unstable = False
print 'ALLOW_UNSTABLE=%s' % allow_unstable

try:
    allow_prerelease = os.environ['ALLOW_PRERELEASE'] in ('1', 'true')
except KeyError:
    print "Optional ALLOW_PRERELEASE is not set. Default to False"
    allow_prerelease = False
print 'ALLOW_PRERELEASE=%s' % allow_prerelease


print "##################################"
print "# Updating AUR with a new PKGBUILD"
print "##################################"


def main():
    release = fetch_release()
    is_unstable = ' ' in release['name']  # because "x.y.z (Beta)"
    if (not release['prerelease'] or allow_prerelease) and (not is_unstable or allow_unstable):
        targz = fetch_targz_link(release)
        pkgbuild = pkgbuild_from_template(targz)
        push_update(pkgbuild)
    else:
        print "This pre-release. Don't update AUR"
        sys.exit(0)


def fetch_release():
    print "Fetching releases from Github..."
    response = urllib2.urlopen('https://api.github.com/repos/ulauncher/ulauncher/releases')
    releases = json.load(response)
    try:
        return (r for r in releases if r['tag_name'] == version).next()
    except StopIteration:
        print "ERROR: Satisfiable release version %s not found" % version
        sys.exit(1)


def fetch_targz_link(release):
    try:
        asset = (a for a in release['assets'] if a['name'].endswith('%s.tar.gz' % version)).next()
    except StopIteration:
        print "ERROR: tar.gz file not found in the release"
        sys.exit(1)

    print "Found tar.gz link %s" % asset['browser_download_url']

    return asset['browser_download_url']


def pkgbuild_from_template(targz):
    template_file = '%s/PKGBUILD.template' % project_path
    with open(template_file) as f:
        content = f.read()
        content = re.sub(r'%VERSION%', version, content, flags=re.M)
        content = re.sub(r'%SOURCE%', targz, content, flags=re.M)
        return content


def push_update(pkgbuild):
    ssh_key = os.sep.join((project_path, 'build-utils', 'aur_key'))
    run_shell(('chmod', '600', ssh_key))
    git_ssh_command = 'ssh -oStrictHostKeyChecking=no -i %s' % ssh_key
    ssh_enabled_env = dict(os.environ, GIT_SSH_COMMAND=git_ssh_command)

    temp_dir = mkdtemp()
    print "Temp dir: %s" % temp_dir
    run_shell(('git', 'clone', aur_repo, temp_dir), env=ssh_enabled_env)
    os.chdir(temp_dir)
    run_shell(('git', 'config', 'user.email', 'ulauncher.app@gmail.com'))
    run_shell(('git', 'config', 'user.name', 'Aleksandr Gornostal'))
    with open('PKGBUILD', 'w') as f:
        f.write(pkgbuild)
    run_shell(('mksrcinfo'))
    run_shell(('git', 'add', 'PKGBUILD', '.SRCINFO'))
    run_shell(('git', 'commit', '-m', 'Version update %s' % version))
    run_shell(('git', 'push', 'origin', 'master'), env=ssh_enabled_env)


def run_shell(command, **kw):
    code = call(command, **kw)
    if code:
        print "ERROR: command %s exited with code %s" % (command, code)
        sys.exit(1)

main()
