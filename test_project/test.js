
function authenticate(username, password) {
    if (!username || !password) {
        throw new Error('Username and password required');
    }
    return validateCredentials(username, password);
}

function validateCredentials(username, password) {
    // Validate against database
    return database.checkUser(username, password);
}
