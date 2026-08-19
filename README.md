# Campus Quick Print

Automated QR-to-Print kiosk platform for mobile upload + instant payment + desktop printing.

## Project Structure

- `/index.html` - Mobile-first web app (Vercel-ready static deployment)
- `/schema.sql` - Supabase PostgreSQL schema + realtime + cleanup cron
- `/agent/print_agent.py` - Windows print agent (auto-download + silent print)
- `/agent/requirements.txt` - Python dependencies for the print agent

## 1) Supabase Setup

1. Create a Supabase project.
2. In **SQL Editor**, run `/schema.sql`.
3. Create a Storage bucket named `print-uploads`.
4. In `/index.html`, replace:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `UPI_ID`
   - `SHOP_ID` (must match `shops.id` in database)
5. Insert at least one shop row in `shops` and use that ID.

## 2) Deploy to Vercel

1. Push this repository to GitHub.
2. Open Vercel → **Add New Project**.
3. Select this repository and deploy.
4. Your web app goes live (for example: `https://campus-quick-print.vercel.app`).

## 3) Windows Desktop Print Agent Setup

1. Copy the `/agent` folder to your Windows PC connected to printer.
2. Install [SumatraPDF](https://www.sumatrapdfreader.org/download-free-pdf-viewer) and place `SumatraPDF.exe` in `/agent`.
3. Open `/agent/print_agent.py` and set:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SHOP_ID`
4. In terminal:

```bash
pip install -r requirements.txt
python print_agent.py
```

The agent watches for jobs where `payment_status = paid` and `print_status = queued`, prints silently, marks status to `printing` then `completed`, and removes temporary local files automatically.

## 4) End-to-End Flow

1. Open the deployed web URL on mobile.
2. Upload up to 10 photos or one PDF.
3. Choose print mode, side mode, copies.
4. App computes pages and total in real time.
5. App uploads PDF to Supabase Storage and creates a `print_jobs` row.
6. App opens UPI deep link: `upi://pay?pa={UPI_ID}&am={AMOUNT}&tn=PRINT-{ORDER_ID}`.
7. Tap **I Have Completed UPI Payment** in UI.
8. Queue tracker updates live: `queued -> printing -> completed`.

## 5) Step 2: What To Do After Agent Generates the Files

### Add Your Keys

- Open `/index.html` and replace `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
- Open `/agent/print_agent.py` and add `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SHOP_ID`.

### Commit & Push to GitHub

```bash
git add .
git commit -m "Initialize automated QR print platform"
git push origin main
```

### Deploy to Vercel

Open Vercel.com → Add New Project → Select your repository → Deploy.

### Test on your PC

Clone/download the `agent/` folder to your Windows PC with printer attached. Place `SumatraPDF.exe` in the same folder, then run:

```bash
pip install -r requirements.txt
python print_agent.py
```

Open the Vercel link on your phone, upload a test file, tap Pay, and verify auto-print flow.
