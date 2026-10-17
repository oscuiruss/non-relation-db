const password = process.env.MONGO_ADMIN_PASSWORD;
if (!password) {
  throw new Error("Set MONGO_ADMIN_PASSWORD before running this script");
}

const admin = db.getSiblingDB("admin");
if (admin.getUser("lab_admin")) {
  print("User lab_admin already exists; no changes made");
} else {
  admin.createUser({
    user: "lab_admin",
    pwd: password,
    roles: [{ role: "root", db: "admin" }]
  });
  print("Created admin user lab_admin");
}

