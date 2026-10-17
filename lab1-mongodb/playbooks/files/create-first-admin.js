const password = process.env.MONGO_ADMIN_PASSWORD;
if (!password) {
  throw new Error("MONGO_ADMIN_PASSWORD is not set");
}

db.getSiblingDB("admin").createUser({
  user: "lab_admin",
  pwd: password,
  roles: [{ role: "root", db: "admin" }]
});

print("Created first administrator lab_admin");
