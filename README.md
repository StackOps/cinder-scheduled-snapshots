# cinder-scheduled-snapshots

Schedule snapshots / backups based in the metadata information stored with the volume information

## What is this?

For some weird reason Cinder does not support scheduled snapshots of volumes (may be scheduling snapshots is something that brilliant minds behind Openstack consider irrelevant, but the fact is that our customer consider it a must and we have extended Openstack to support this feature).

# How it works.

the plugin for Cinder in StackOps Portal allows daily and weekly scheduling for snapshots. Internally, we change the metadata of the volume to add the following attributes:

- display_description: Full description given to the snapshots. Informational only.
- backup_type: daily or weekly.
- rotation: Number of snapshot retained. Older than this number will be deleted.
- schedule_backup: Hour and minute of the day the snapshot will take place.

# The application

In the stackops.ini file you can configure the user, keystone endpoint and others.

This application needs as argument a password with enough permissions to access to all the tenants in your system (an admin role?) because it checks the metadata of all the volumes.

# Running the application

You should put this app inside the crontab and execute it at 00:00. The application will then use the 'at' command in linux to schedule them. It's also important that the lifetime of the user tokens last for 24 hours.

# Using this script with a vanilla Openstack

if you want to use this script with a vanilla Openstack, you will have to enter manually the metadata in the volume you want to backup.

# Final notes

Use at your own risk and have fun!

