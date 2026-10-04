document
    .getElementById("registerForm")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const name =
            document.getElementById("name").value.trim();

        const studentId =
            document.getElementById("studentId").value.trim();

        const email =
            document.getElementById("email").value.trim();

        const department =
            document.getElementById("department").value.trim();

        const semester =
            document.getElementById("semester").value;

        const password =
            document.getElementById("password").value;

        const confirmPassword =
            document.getElementById("confirmPassword").value;

        const message =
            document.getElementById("registerMessage");


        // Check passwords
        if (password !== confirmPassword) {

            message.textContent =
                "Passwords do not match.";

            return;
        }


        try {

            const response = await fetch(
                "http://127.0.0.1:5000/api/register",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        name: name,
                        student_id: studentId,
                        email: email,
                        department: department,
                        semester: semester,
                        password: password
                    })
                }
            );


            const data = await response.json();


            if (response.ok) {

                message.textContent =
                    "Registration successful!";

                setTimeout(function() {

                    window.location.href = "login.html";

                }, 1000);

            } else {

                message.textContent =
                    data.message || "Registration failed.";
            }


        } catch (error) {

            console.error("Registration error:", error);

            message.textContent =
                "Unable to connect to Flask server.";
        }

    });