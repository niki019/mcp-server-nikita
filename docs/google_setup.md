# 🔑 Google Workspace API Setup Guide

This guide details how to create a Google Cloud Project, enable the Google Docs and Gmail APIs, configure the OAuth Consent Screen, and download the `credentials.json` client secrets file required by our custom Workspace MCP server.

---

## Step 1: Create a Google Cloud Project
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with the Google Account that hosts the Google Doc you want to append reports to and the Gmail account you want to send mail from.
3. Click the project dropdown in the top-left corner and select **New Project**.
4. Set the project name (e.g., `Weekly-Review-Pulse`) and click **Create**.
5. Once created, make sure your new project is selected in the top-left dropdown.

---

## Step 2: Enable the APIs
You must enable both the **Google Docs API** and the **Gmail API**:
1. In the left-hand sidebar, navigate to **APIs & Services** > **Library**.
2. Search for `Google Docs API`, click it, and click **Enable**.
3. Go back to the Library, search for `Gmail API`, click it, and click **Enable**.

---

## Step 3: Configure the OAuth Consent Screen
Since this application runs locally and connects directly to Google APIs using your user account, you must register it under the OAuth Consent Screen:
1. In the left-hand sidebar, navigate to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (or **Internal** if you are using a Google Workspace organization account) and click **Create**.
3. Fill out the **App Information**:
   * **App name**: `Weekly Review Pulse`
   * **User support email**: *Your Gmail address*
   * **Developer contact email**: *Your Gmail address*
4. Click **Save and Continue**.
5. **Scopes**: Click **Add or Remove Scopes**. In the filter, search for and select the following scopes:
   * `.../auth/documents` (Google Docs - view and manage documents)
   * `.../auth/gmail.send` (Gmail - send emails on your behalf)
6. Click **Update** and then **Save and Continue**.
7. **Test Users**: Under Test Users, click **+ Add Users** and enter your own Gmail address. *(This is critical because the app is in "Testing" mode and will only allow logins from registered test users)*.
8. Click **Save and Continue** and review the summary.

---

## Step 4: Create OAuth Client Credentials
1. In the left-hand sidebar, navigate to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** at the top of the screen and select **OAuth client ID**.
3. In the **Application type** dropdown, select **Desktop app**.
4. Set the name to `Pulse-Desktop-App` and click **Create**.
5. A modal will pop up saying "OAuth client created". Click **OK**.

---

## Step 5: Download and Save `credentials.json`
1. On the Credentials page, find your new client under the **OAuth 2.0 Client IDs** table.
2. Click the **Download JSON** icon (downward pointing arrow) on the far right of the row.
3. Save the downloaded file to your local computer.
4. Rename this file to exactly `credentials.json`.
5. Place this file inside the `e:\weekly-review-pulse\mcp_server\` directory.

---

## Step 6: Initial Authentication Flow
When you run the MCP server or the core pipeline for the first time:
1. The script will look for `credentials.json` in `mcp_server/`.
2. It will launch a local web server and open your default browser to a Google sign-in page.
3. Log in using your test Gmail account.
4. You may see a warning saying *"Google hasn't verified this app"*. This is normal for apps in testing mode. Click **Advanced** > **Go to Weekly Review Pulse (unsafe)**.
5. Grant the permissions to view/manage your documents and send email.
6. Once completed, the browser will display *"The authentication flow has completed. You may close this window."*
7. A file named `token.json` will be automatically generated inside `mcp_server/`. This token will be used to silently authenticate all subsequent runs.
