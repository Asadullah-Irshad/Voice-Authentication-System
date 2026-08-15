# Publishing to GitHub

A step-by-step checklist to get this repository live and looking its best.

## 1. Pre-flight

- [ ] Delete the `_to_delete/` folder if it exists (leftover transfer archives).
- [ ] Confirm there is **no** real `.env` file (only `.env.example` should be committed).
- [ ] Confirm `data/` and `workspaces/` are absent or empty (they're git-ignored).
- [ ] Skim the README once in a Markdown previewer to check images render.

## 2. Create the repository

On [github.com/new](https://github.com/new):

- **Repository name:** `Voice-Authentication-System`
- **Description (paste this):**
  > AI-powered voice biometric authentication using SpeechBrain and ECAPA-TDNN for secure speaker verification.
- **Visibility:** Public
- Do **not** initialise with a README, .gitignore, or license (this repo already has them).

## 3. Push the code

From inside the project folder:

```bash
git init
git add .
git commit -m "Voice Authentication System v2.0.0"
git branch -M main
git remote add origin https://github.com/asadullahirshad3/Voice-Authentication-System.git
git push -u origin main
```

> Prefer the web UI? Use **Add file → Upload files** and drag the folder contents in.
> Make sure the hidden `.github/`, `.gitignore`, and `.env.example` are included.

## 4. Add Topics (for discoverability)

On the repo page, click the ⚙️ next to **About** and add these topics:

```
voice-authentication  speaker-recognition  speaker-verification  ecapa-tdnn
speechbrain  voice-biometrics  audio-processing  deep-learning  machine-learning
pytorch  fastapi  python  jwt  docker  rest-api  privacy-first
```

## 5. Polish the repo page

- [ ] In **About**, add the description above and tick **Releases** / **Packages** as desired.
- [ ] Enable **Issues** and **Discussions** if you want community feedback.
- [ ] (Optional) Add a repository social preview image (Settings → General → Social preview);
      `Docs/Screenshots/hero-landing.png` works well.
- [ ] Confirm the **Actions** tab shows the CI workflow running (green check).
- [ ] (Optional) Create a **v2.0.0 release** and paste the top of `CHANGELOG.md` as the notes.

## 6. After it's live

- [ ] Check the CI badge in the README turns green.
- [ ] Verify every screenshot and the walkthrough GIF display on the rendered README.
- [ ] Share the link 🎉
