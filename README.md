# Pacman-Update-Monitor
Enables Pacman update monitoring via standalone script with no external dependencies.
## How to set up
* Modify `email.json` and specify all needed email settings
* (Optional) Modify `repos.txt` to add extra repositories other than defaults
* (Optional) If there is no `/etc/pacman.d/mirrorlist` file you can create a `mirror.txt` file in the script directory specifying the prefered repository mirror (probably will be changed at some point)
* Use some task scheduler like Cron to automatically run the `update_monitor.py` script (i'd recommend once a day)

## Known bugs:
* Manually installed newer versions (via `pacman -U`) aren't detected properly if the version in question is not indexed in official mirrors.
