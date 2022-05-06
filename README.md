# Pacman-Update-Monitor
Enables Pacman update monitoring via standalone script with only one external dependecy (requests)
## How to set up
* Modify email.json and specify all needed email settings
* (Optional) Modify repos.txt to add extra repositories other than defaults
* (Optional) If there is no /etc/pacman.d/mirrorlist file you can create a mirror.txt file in the script directory specifying the prefered repository mirror (probably will be changed at some point)
* Use some task scehduler like Cron to automatically run the update_monitor.py script (i'd recommend once a day)
