# 🤖 AshBolt Telegram Bot — Course Selling Flow (₹29 Namaste React)

---

## 🔰 Overview

This bot is designed to automate the sale and delivery of the Namaste React Course for a one-time fee of ₹29. It ensures fair promotion and manual payment verification by forwarding user receipts to the admin before giving access.

---

## 👣 User Flow

### 1. `/start`

* Greets the user
* Button: `🔥 Buy Course At Just ₹29`

### 2. `🔥 Buy Course`

* Sends instructions to:

  * Share the promo message to 3 Telegram groups
  * Take 3 screenshots
  * Submit screenshots
* Sends promo image and caption
* Button: `📤 Submit Screenshots`

### 3. `📤 Submit Screenshots`

* User uploads 3 screenshots (one by one)
* Bot tracks the number of screenshots
* After 3 are submitted:

  * Sends UPI ID and QR code
  * Button: `📥 Send Payment Receipt`
  * Warning: `⚠️ Fake UTRs will be banned and blocked!`

### 4. `📥 Send Payment Receipt`

* User uploads payment screenshot (image or image document)
* Bot forwards it to ADMIN\_ID
* User sees:

  * `✅ Payment screenshot sent to admin for review. Please wait for approval.`

---

## 🛡️ Admin Flow

### Forwarded Payment Receipt

* Admin receives screenshot + two buttons:

  * `✅ Approve`
  * `❌ Reject`

### If `✅ Approve` clicked:

* User receives:

  * `🎉 Payment Approved! Here's your course access:`
  * `https://1024terabox.com/s/1F_FRmqIs_1HpALb7zUlM0g`
  * `🔑 Password: 7878`
* Admin sees: `✅ Access sent to user {user_id}`

### If `❌ Reject` clicked:

* User receives:

  * `❌ Payment not accepted. Please ensure it's correct and try again.`
* Admin sees: `❌ Rejected payment for user {user_id}`

---

## ⚙️ Internal State

* `user_state` — Current flow stage of each user
* `user_screenshot_counter` — Tracks screenshot uploads
* `payment_proofs` — Maps user\_id to payment message for admin approval

---

## 🔐 Security & Anti-Abuse

* Manual review ensures only legit payments are accepted
* Fake screenshots cannot bypass access
* Clear warning message to discourage fraud

---

## ✅ Optional Future Features

* Auto-block after repeated fake attempts
* Logging to Google Sheets or SQLite
* Unique tokenized course access links
* Admin dashboard (Telegram or Web)

---

## 📦 Final Course Delivery Message

```
✅ Payment Approved!
Here is your course access link:
🔗 https://1024terabox.com/s/1F_FRmqIs_1HpALb7zUlM0g
🔑 Password: 7878
```

---

## 📁 Files & Media

* Promo Image: `https://i.postimg.cc/dtSLLGJ2/akl.png`
* QR Image: `https://i.postimg.cc/3N67GnpM/qr.jpg`

---

## 🙋 Contact

For any help, user can reach out to admin:

* Telegram: `@iam_akilesh07`

---



"# Ashbolt-Telegram-Bot" 
DEPLOY RENDER - https://chatgpt.com/share/6846e3dd-4bc4-8001-8516-d39a1e14494f

BOT CREATION - https://chatgpt.com/share/6846e720-d558-8001-9ac0-1d556d23224b
