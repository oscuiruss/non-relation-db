const password = process.env.MONGO_ADMIN_PASSWORD;
if (!password) {
  throw new Error("MONGO_ADMIN_PASSWORD is not set");
}

const admin = db.getSiblingDB("admin");
admin.auth("lab_admin", password);
print("Authenticated as lab_admin");
