# Deploy to Streamlit Community Cloud

The repository includes everything needed to serve the dashboard. No API keys, raw customer records or database server are required.

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) and connect the GitHub account that owns this repository.
2. Select **Create app**, then deploy from GitHub.
3. Select repository `uniyal802/olist-delivery-seller-analysis`.
4. Branch: `main`. Main file: `streamlit_app.py`.
5. In Advanced settings, select Python **3.13**. Dependencies are defined in `requirements.txt`.
6. Choose an available app subdomain and select **Deploy**.
7. Confirm that the page loads and shows **99,441 orders** and **6.77% late-delivery rate**.
8. Check purchase year **2017**, customer state **RJ**: **6,225 orders**, **10.46% late rate**. Reset the filters.
9. Set the app to public sharing if it is not public already. Copy the actual `https://...streamlit.app` URL into the README and resume.

An app URL is only valid after deployment succeeds. This guide does not reserve a subdomain or claim that deployment has occurred.

## Required deployment files

- `streamlit_app.py`
- `requirements.txt`
- `reports/app_data.json.gz`
- `.streamlit/config.toml` (theme settings)

The compressed data file contains aggregate counts and sums used for the filters and charts. It is small enough to store directly in Git. Do not omit it when copying the project.

## Test locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v test_streamlit.py
python -m streamlit run streamlit_app.py
```

## Refresh data

```bash
python3 run_project.py --download
python3 prepare_streamlit.py
python3 -m unittest -v test_project.py
```

Review the generated report and commit the updated aggregate snapshot. Do not commit raw CSVs, the database, virtual environments or secrets. After an updated commit, check the live app and its build logs.

Official instructions: [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
