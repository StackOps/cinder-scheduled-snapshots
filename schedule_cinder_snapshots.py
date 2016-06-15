# coding=utf-8

"""
   Copyright 2011-2016 STACKOPS TECHNOLOGIES S.L.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

#
#  python schedule_cinder_snapshots.py ADMIN_PASSWORD
#

import sys
import logging
import logging.config
import json
import subprocess
import ConfigParser

from datetime import datetime, timedelta

from openstacklibs.keystone import Keystone
from openstacklibs.cinder import Cinder

numargs = len(sys.argv)
if numargs>2:
    initfile = str(sys.argv[2])
else:
    initfile = "./stackops.ini"

logging.config.fileConfig(initfile)
logging.captureWarnings(True)

logger_ = logging.getLogger(__name__)

config = ConfigParser.ConfigParser()
config.read(initfile)

usr = config.get('keystone', 'username')
admin_tenant_name = config.get('keystone', 'tenant')
keystone_url = config.get('keystone', 'url')
volume_url = config.get('cinder', 'url')

logger_.debug("USERNAME:%s" % usr)
logger_.debug("TENANT:%s" % admin_tenant_name)
logger_.debug("KEYSTONE URL:%s" % keystone_url)
logger_.debug("CINDER URL:%s" % volume_url)

usr = "admin"

total = len(sys.argv)
cmdargs = str(sys.argv)
passw = str(sys.argv[1])
os_admin_tenant_name = admin_tenant_name

adminKeystoneObj = Keystone(keystone_url, usr, passw, os_admin_tenant_name)
cinderObj = Cinder(adminKeystoneObj.getToken(), volume_url)
tenant = adminKeystoneObj.getTenant(os_admin_tenant_name)

if tenant is not None:
    tenant_enabled = tenant['enabled']
    tenant_id = tenant['id']
    # Iterate over all available volumes in the system
    volumes = cinderObj.get_all_global_volumes(tenant_id)['volumes']
    for volume in volumes:
        id = volume['id']
        name = volume['display_name']
        meta = volume['metadata']
        owner_id = volume['os-vol-tenant-attr:tenant_id']
        created_at = datetime.strptime(volume['created_at'], '%Y-%m-%dT%H:%M:%S.%f')
        if 'type' in meta and 'rotation' in meta and 'backup_type' in meta and 'schedule_backup' in meta:
            # We have found the scheduled backup metadata information, so we have to process it.
            description = meta['display_description']
            backup_type = meta['backup_type']
            rotation = int(meta['rotation'])
            schedule_backup = meta['schedule_backup']
            if backup_type == 'weekly':
                # if weekly backup, then rotation and retetion is weekly too
                rotation *= 7
            hour = schedule_backup.split(':')[0]
            minutes = schedule_backup.split(':')[1]
            if backup_type == 'daily' or created_at.weekday() == datetime.today().weekday():
                # First let's get the token for this tenant
                localKeystoneObj = Keystone(keystone_url, usr, passw, '', tenantid = owner_id)
                localCinderObj = Cinder(localKeystoneObj.getToken(), volume_url)

                # If daily backup or is the day of the weekly backup, go for it
                print "Schedule snapshot for today: %s, %s, %s, %s, %s, %s" % (
                    id, name, backup_type, rotation, schedule_backup, description)
                logger_.info("Schedule snapshot for today: %s, %s, %s, %s, %s, %s" % (
                    id, name, backup_type, rotation, schedule_backup, description))
                display_name = "Scheduled snapshot launched on %s at %s:%s" % (
                    datetime.strftime(datetime.today(), "%Y-%m-%d"), hour, minutes)
                display_description = display_name
                url = "%s/%s/snapshots" % (volume_url, owner_id)
                payload = {
                    "snapshot": {"display_name": display_name.encode('ascii'), "force": "True",
                                 "display_description": display_description.encode('ascii'),
                                 "volume_id": id.encode('ascii')}}

                # The command to schedule today
                create_command = """curl -g -i -X POST %s -H \\"Content-Type: application/json\\" -H \\"Accept: application/json\\" -H \\"X-Auth-Token: %s\\" -d \\'%s\\' """ % (
                    url, localKeystoneObj.token_, json.dumps(payload, ensure_ascii=True).replace('"','\\"'))

                at_command = """`echo %s | at %s%s`""" % (create_command, hour, minutes)
                subprocess.call(at_command, shell=True)

                # Now we have to schedule the command to delete the rotational snapshot
                # We are going to figure out the snapshot based on the name and create a delete command
                # Does exists a snapshot made X days ago with the same string in the name?
                display_name_to_delete = "Scheduled snapshot launched on %s at %s:%s" % (
                    datetime.strftime(datetime.today() - timedelta(days=rotation), "%Y-%m-%d"), hour, minutes)
                current_snapshots = localCinderObj.get_all_snapshots(owner_id)
                for snapshot in current_snapshots['snapshots']:
                    if snapshot['display_name'].encode('ascii') == display_name_to_delete:
                        # Ok, we found a snapshot. Let's create the command to delete it.
                        snapshot_id = snapshot['id']
                        print "Schedule delete for today: %s" % (snapshot_id)
                        logger_.info("Schedule delete for today: %s" % (snapshot_id))
                        url = "%s/%s/snapshots/%s" % (volume_url, owner_id, snapshot_id)
                        # The command to schedule DELETE today
                        # The command to schedule today
                        delete_command = """curl -g -i -X DELETE %s -H \\"Content-Type: application/json\\" -H \\"Accept: application/json\\" -H \\"X-Auth-Token: %s\\" """ % (
                            url, localKeystoneObj.token_)

                        at_command = """`echo "%s" | at %s%s`""" % (delete_command, hour, minutes)
                        subprocess.call(at_command, shell=True)





