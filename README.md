# Schengen Slot Checker — Setup Guide

Runs every 5 minutes on GitHub's servers for FREE.
Sends a push notification to your phone when a slot opens.

---

## Step 1 — Create a free GitHub account
https://github.com/signup  (skip if you already have one)

---

## Step 2 — Create a new repository

1. Go to https://github.com/new
2. Name it:  schengen-checker
3. Set it to **Private**
4. Click "Create repository"

---

## Step 3 — Upload the files

Upload these two files to the repo root:
- check.py
- .github/workflows/check.yml

Easiest way:
1. On the repo page click "uploading an existing file"
2. Drag both files in
3. Click "Commit changes"

NOTE: The .github/workflows/ folder must exist exactly like that.
If drag-and-drop doesn't create the folder, use GitHub Desktop
or the instructions below to create it manually.

### Creating the workflow folder manually:
1. Click "Add file" -> "Create new file"
2. In the filename box type:  .github/workflows/check.yml
3. Paste the contents of check.yml
4. Commit it

---

## Step 4 — Set up your secrets (ntfy topic etc.)

1. In your repo go to:  Settings -> Secrets and variables -> Actions
2. Click "New repository secret"
3. Add these two secrets:

   Name:  NTFY_TOPIC
   Value: schengen-lenovo-alerts   <- or whatever topic you chose in ntfy app

   Name:  WEBHOOK_URL
   Value: https://webhook.site/4a1f1e17-a6b4-40d4-8906-9022f56980d2

---

## Step 5 — Set up ntfy on your phone (if not done already)

1. Install ntfy app:
   Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy
   iOS:     https://apps.apple.com/app/ntfy/id1625396347

2. Open app -> tap + -> subscribe to:  schengen-lenovo-alerts

---

## Step 6 — Test it manually

1. Go to your repo on GitHub
2. Click the "Actions" tab
3. Click "Schengen Slot Checker" on the left
4. Click "Run workflow" -> "Run workflow"
5. Watch the run — if it completes with a green tick, you're live!

---

## That's it!

GitHub will now run check.py every 5 minutes automatically.
When a slot opens you'll get a push notification on your phone.
You can watch all runs in the Actions tab.

---

## Free tier limits (you won't hit these)

GitHub gives free accounts 2,000 minutes/month for private repos.
Each run takes ~20 seconds, so 5-min intervals = ~8,600 minutes/month needed...

WAIT — that exceeds the limit for private repos!

SOLUTION: Make the repo PUBLIC (the code has no passwords in it —
all sensitive values are in Secrets). Public repos get UNLIMITED
free minutes. Go to Settings -> Danger Zone -> Change visibility -> Public.
