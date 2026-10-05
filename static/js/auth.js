// static/js/auth.js
// Browser-side helpers for the /auth endpoints. Served at /static/js/auth.js
//
//   <script src="/static/js/auth.js"></script>
//   <script>
//     Auth.signUp("me@example.com", "password123").then(console.log);
//     Auth.logIn("me@example.com", "password123").then(console.log);
//   </script>

(function (global) {
  "use strict";

  async function post(path, email, password) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password }),
    });

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      /* empty or non-JSON body */
    }

    if (!res.ok) {
      const err = new Error((data && data.error) || "Request failed (" + res.status + ")");
      err.status = res.status;
      throw err;
    }
    return data;
  }

  const Auth = {
    // POST /auth/signup -> 201 with the user object
    signUp: function (email, password) {
      return post("/auth/signup", email, password);
    },

    // POST /auth/login -> 200 { access_token, refresh_token }
    // Tokens are kept in memory only (not localStorage) so XSS can't read them from storage.
    logIn: async function (email, password) {
      const data = await post("/auth/login", email, password);
      Auth._accessToken = data.access_token;
      Auth._refreshToken = data.refresh_token;
      return data;
    },

    // Header to attach to protected requests later on.
    authHeader: function () {
      return Auth._accessToken ? { Authorization: "Bearer " + Auth._accessToken } : {};
    },

    logOut: function () {
      Auth._accessToken = null;
      Auth._refreshToken = null;
    },

    _accessToken: null,
    _refreshToken: null,
  };

  global.Auth = Auth;
})(window);
