
In order to run this project, do the following: 
```bash
sudo service postgresql start

streamlit run ui/advisor_page.py 
```
Note: github prevent me from pushing this commit because of the large datasaet (of embeddings of news, so ill just delete it since we don't use it anymore) also thr prices .csv

i did :

# Remove any oversized CSVs not tracked by git
find analysis -name "*.csv" -size +100M -delete

# Commit and push
git add README.md .gitignore
git commit -m "Clean up: remove large files and update gitignore"
git push