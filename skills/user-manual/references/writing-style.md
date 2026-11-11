# Writing Style: Plain Language for Non-Technical Readers

The reader is a busy person who has never used the app and does not know technical words. They read one step, do it, and then look back at the page. Write for them.

## Core rules

1. **Talk to the reader.** Use "you" ("Anda" in Indonesian). Use active voice: "Click **Save**", not "The Save button should be clicked".
2. **One action per step.** If a step contains "and then", split it.
3. **Start each step with the action verb**: Click, Tap, Type, Choose, Open, Scroll. In Indonesian: Klik, Ketuk, Ketik, Pilih, Buka, Gulir.
4. **Say where before what.** "In the top-right corner, click **Profile**." The reader finds the place first, then the button.
5. **Name on-screen items exactly as they appear**, in **bold**, with the same capitalization. Never rename a button.
6. **Say what happens next.** After an important step, add one short sentence on the result: "The Orders page opens."
7. **Short sentences.** Aim for 20 words or fewer. Keep paragraphs to 3 sentences or fewer.
8. **Explain the reason in one sentence** before a task: "Do this when a customer wants their money back."
9. **No jargon, no abbreviations.** If a technical term is unavoidable (it appears on screen), explain it the first time and add it to the Glossary.
10. **Keep words consistent.** Pick one word per action ("click" for computers, "tap" for phones) and one name per thing. Use them everywhere.
11. **Friendly and calm.** Never blame the reader. For errors, say what to do: "If you see **Wrong password**, type it again slowly. Check that Caps Lock is off."
12. **No developer content.** No code, file paths, API, database, server, or log details. Anything the reader cannot see on screen does not belong in the manual.

## Structure of each task (subsection)

1. Title phrased as a goal: "Create a new invoice", "Membuat faktur baru"
2. One-sentence purpose (when and why)
3. Optional "Before you start" list (things the reader needs: account, permission, documents)
4. Numbered steps (`steps` block). Put a screenshot after the step it shows, or after the whole list.
5. Result: what the reader sees when it worked
6. Optional `tip`, `note`, or `warning` box. Use `warning` only when data could be lost, money moved, or something cannot be undone.

## Screenshots

- One screenshot per screen the reader reaches. Don't screenshot every click.
- Number the markers to match the steps: marker **1** = step 1.
- The caption describes what the picture shows in plain words: "The New Invoice form", not "invoice_create.png".
- Mention the picture in the text when it helps: "(see Figure 3.2)".

## Word replacements

| Avoid | English | Bahasa Indonesia |
|---|---|---|
| authenticate / log in credentials | sign in / your username and password | masuk / nama pengguna dan kata sandi |
| navigate to | go to / open | buka |
| URL / link address | web address | alamat situs |
| browser | web browser (e.g. Chrome) | peramban (misalnya Chrome) |
| dropdown / select box | list (click the list and choose …) | daftar pilihan |
| toggle | switch (turn on / turn off) | tombol geser (aktifkan / nonaktifkan) |
| checkbox | tick box (tick / untick) | kotak centang (centang / hapus centang) |
| radio button | option (choose one) | pilihan |
| modal / dialog / popup | window / small window | jendela |
| input field / text field | box | kolom |
| submit | click **Send** / **Save** (use the on-screen word) | klik **Kirim** / **Simpan** |
| tab (UI) | tab (only if it looks like a tab; otherwise "section") | tab / bagian |
| icon | picture / symbol (describe it: "the pencil symbol") | ikon / gambar (jelaskan: "gambar pensil") |
| hamburger menu | menu button (three lines ☰) | tombol menu (tiga garis ☰) |
| cache / cookies | (avoid; say "close and reopen the browser") | (hindari; "tutup lalu buka kembali peramban") |
| refresh / reload | reload the page (press F5) | muat ulang halaman (tekan F5) |
| error / exception | message / problem | pesan / masalah |
| data / record / entry | the specific thing: order, customer, item | sebutkan bendanya: pesanan, pelanggan, barang |
| execute / run / perform | do / start | lakukan / mulai |
| configure / settings | change settings / set up | atur / ubah pengaturan |
| delete permanently | remove (this cannot be undone) | hapus (tidak bisa dibatalkan) |
| upload / download | add a file from your computer / save a copy to your computer | unggah (tambahkan berkas dari komputer) / unduh (simpan salinan ke komputer) |
| sync | update | perbarui |
| user role / permission | what you are allowed to do | hak akses (apa yang boleh Anda lakukan) |

For other languages, apply the same idea: the everyday word the reader would say aloud.

## Standard chapters (when the user picks "Standard")

1. **Introduction**: what the app is for, who it is for, how to use this manual (bold = on-screen words; red boxes and numbers in pictures)
2. **Getting Started**: what you need (device, internet, account), opening the app, signing in, signing out, the main screen tour (one annotated screenshot with numbered parts and a matching list), forgotten password
3. … **one chapter per menu or feature**, in the order the menu shows them
4. **Troubleshooting and FAQ**: problem → what to do, as a table or short subsections
5. **Glossary**: on-screen terms explained in one sentence each (table)

"By role": Introduction, Getting Started, one chapter per role (its tasks as subsections), Troubleshooting, Glossary.
"By task": Introduction, Getting Started, chapters grouped by goal ("Daily work", "Month-end", …) with each task as a subsection, Troubleshooting, Glossary.

## Final read-through checklist

- [ ] No word from the Avoid column, no abbreviations left unexplained
- [ ] Every step starts with a verb and names exactly one action
- [ ] Every button/field name is bold and matches the screen exactly
- [ ] Every screenshot has a caption; marker numbers match step numbers
- [ ] No real personal data visible in any screenshot
- [ ] Each task says what success looks like
