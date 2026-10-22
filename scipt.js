const API_URL = "https://edu-studio-681e.onrender.com";


// CREATE USER
async function createUser() {

    const username =
        document.getElementById("username").value;

    const email =
        document.getElementById("email").value;

    const password =
        document.getElementById("password").value;


    const response = await fetch(`${API_URL}/users`, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            username: username,
            email: email,
            password: password
        })
    });


    const data = await response.json();


    if (!response.ok) {

        showMessage(data.detail);

        return;
    }


    showMessage(
        `User ${data.username} created successfully!`
    );


    getUsers();
}



// GET USERS
async function getUsers() {

    const response =
        await fetch(`${API_URL}/users`);


    const users =
        await response.json();


    const usersContainer =
        document.getElementById("users");


    usersContainer.innerHTML = "";


    users.forEach(user => {

        const userElement =
            document.createElement("div");


        userElement.className = "user";


        userElement.innerHTML = `
            <strong>ID:</strong> ${user.id}
            <br>

            <strong>Username:</strong>
            ${user.username}

            <br>

            <strong>Email:</strong>
            ${user.email}

            <br><br>

            <button onclick="selectUser(${user.id})">
                Edit
            </button>

            <button onclick="deleteUserById(${user.id})">
                Delete
            </button>
        `;


        usersContainer.appendChild(userElement);
    });
}



// GET SINGLE USER
async function selectUser(id) {

    const response =
        await fetch(`${API_URL}/users/${id}`);


    const user =
        await response.json();


    if (!response.ok) {

        showMessage(user.detail);

        return;
    }


    document.getElementById("updateId").value =
        user.id;

    document.getElementById("updateUsername").value =
        user.username;

    document.getElementById("updateEmail").value =
        user.email;
}



// UPDATE USER
async function updateUser() {

    const id =
        document.getElementById("updateId").value;

    const username =
        document.getElementById("updateUsername").value;

    const email =
        document.getElementById("updateEmail").value;


    const response = await fetch(
        `${API_URL}/users/${id}`,
        {

            method: "PUT",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username: username,
                email: email
            })
        }
    );


    const data =
        await response.json();


    if (!response.ok) {

        showMessage(data.detail);

        return;
    }


    showMessage("User updated successfully!");

    getUsers();
}



// DELETE USER
async function deleteUser() {

    const id =
        document.getElementById("deleteId").value;


    deleteUserById(id);
}



async function deleteUserById(id) {

    const response = await fetch(
        `${API_URL}/users/${id}`,
        {
            method: "DELETE"
        }
    );


    const data =
        await response.json();


    if (!response.ok) {

        showMessage(data.detail);

        return;
    }


    showMessage(data.message);

    getUsers();
}



// MESSAGE
function showMessage(message) {

    document.getElementById("message")
        .textContent = message;
}
