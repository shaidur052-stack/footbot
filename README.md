cd D:\llama\nutribot-bd\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload




cd D:\llama\nutribot-bd\frontend
npm run dev

pip install -r .\backend\requirements.txt


cd .\frontend
npm install