# Deployment Guide: Treefolk Atlas

This guide walks you through deploying **Treefolk Atlas** to GitHub, hosting it on Streamlit Community Cloud, and integrating it onto your personal website at `solarpunked.online/treefolk`.

---

## 1. Push to GitHub

The project has been initialized as a local Git repository and the files have been committed. Follow these steps to push it to your GitHub account:

1. Open your terminal in the project directory: `d:\Leonanda's Professional Vault\Projects\itree-sea`.
2. Rename the default branch to `main`:
   ```bash
   git branch -M main
   ```
3. Go to [GitHub](https://github.com/) and create a new repository:
   - **Repository name:** `treefolk-atlas` (or your preferred name)
   - **Visibility:** Public (or Private)
   - **Do not** initialize with a README, `.gitignore`, or license (as they are already present in the workspace).
4. Run the following commands in your local terminal to link your local repository to the new GitHub repository and push your code:
   ```bash
   git remote add origin https://github.com/leonanda-vault/treefolk-atlas.git
   git push -u origin main
   ```

---

## 2. Deploy to Streamlit Community Cloud

Streamlit Community Cloud is a free hosting platform specifically designed for Streamlit apps.

1. Go to [share.streamlit.io](https://share.streamlit.io/) and click **Sign in with GitHub**.
2. Once logged in, click the **New app** button.
3. Configure the deployment settings:
   - **Repository:** `leonanda-vault/treefolk-atlas`
   - **Branch:** `main`
   - **Main file path:** `itree_sea/dashboard.py`
4. Click **Deploy**.

> [!NOTE]
> The app is configured to automatically create and seed the SQLite database (`itree_sea.db`) from `data/seed_species.csv` when it boots up for the first time in the cloud environment.

---

## 3. Host at `solarpunked.online/treefolk`

Since `solarpunked.online` is built with plain HTML, it cannot run Python/Streamlit directly on the same static file hosting. However, you can seamlessly embed your running Streamlit Cloud app into your website.

### Option A: Embed via iframe (Recommended for Static Hosting)

You can create a folder named `treefolk` in your website source directory and place an `index.html` file inside it. Use the code block below:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Treefolk Atlas - Carbon & Ecosystem Calculator</title>
    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #0d1f17; /* Matches dashboard theme background */
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
    </style>
</head>
<body>
    <!-- Replace URL with your deployed Streamlit URL. Note the ?embed=true query parameter -->
    <iframe src="https://treefolk-atlas.streamlit.app/?embed=true"></iframe>
</body>
</html>
```

> [!TIP]
> The `?embed=true` parameter tells Streamlit to automatically hide its header, footer, and sidebar options, making the embedded app look like a native part of your website.

---

### Option B: Host on your own VPS (Self-Hosted Backend)

If you own a virtual private server (VPS) for `solarpunked.online` and want to run it directly:

1. Clone the repository on your server:
   ```bash
   git clone https://github.com/leonanda-vault/treefolk-atlas.git
   cd treefolk-atlas
   ```
2. Build the environment and run Streamlit in the background:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   nohup streamlit run itree_sea/dashboard.py --server.port 8501 --server.address 127.0.0.1 &
   ```
3. Set up **Nginx** reverse proxy in your site configuration file to forward `/treefolk` requests to the Streamlit port:
   ```nginx
   location /treefolk {
       proxy_pass http://127.0.0.1:8501;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_real_ip_header X-Real-IP;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   ```
4. Restart Nginx: `sudo systemctl restart nginx`.
