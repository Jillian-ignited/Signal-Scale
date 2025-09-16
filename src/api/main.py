# Replace the API file
cp enterprise-brand-intelligence-api.py src/api/main.py

# Commit and deploy
git add src/api/main.py
git commit -m "Upgrade to enterprise brand intelligence engine"
git push origin main
