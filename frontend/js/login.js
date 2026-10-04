document.getElementById("loginForm").addEventListener("submit", async function(event) {

    event.preventDefault();

    const username =
        document.getElementById("username").value.trim();

    const password =
        document.getElementById("password").value;

    const message =
        document.getElementById("loginMessage");


    if (username === "" || password === "") {

        message.textContent =
            "Please enter your username and password.";

        return;
    }


    try {

        const response = await fetch(
            "http://127.0.0.1:5000/api/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    username: username,
                    password: password

                })
            }
        );


        const data = await response.json();


        if (response.ok) {

            message.textContent =
                "Login successful!";


            // Save login information temporarily
            localStorage.setItem(
                "student",
                JSON.stringify(data)
            );


            setTimeout(function() {

                window.location.href =
                    "dashboard.html";

            }, 700);

        } else {

            message.textContent =
                data.message || "Login failed.";

        }


    } catch (error) {

        console.error("Login error:", error);

        message.textContent =
            "Unable to connect to Flask server.";

    }

});