BookNStay

Tech Stack: Python, Flask, MySQL, SMTP (for email OTP)

This was a personal project I built to help hotel owners manage their day-to-day operations more efficiently. The system allows hotel staff to register new customers, allocate rooms, track room status (like available, under cleaning, or occupied), generate bills, and even handle food orders linked to specific room numbers.

I developed a backend system using Flask where hotel owners can add their property, manage rooms, and view bookings.

Built a feature that sends an OTP to the customer’s email when a food order is placed from a room, and confirms the order only after OTP verification.

Room states can be updated in real time, which helps the staff know which rooms are available or need cleaning.

Generated digital bills for each booking with itemized services (room + food) and allowed the user to download the receipt.

Optimized SQL queries to make the system faster, especially when fetching available rooms or generating booking lists.

Why it’s useful:
This project made hotel management much easier for owners. Instead of using paper registers or Excel sheets, everything is managed in one place — from assigning rooms to billing and food orders. It reduces manual errors, saves time, and makes operations smoother for small to mid-sized hotels.
