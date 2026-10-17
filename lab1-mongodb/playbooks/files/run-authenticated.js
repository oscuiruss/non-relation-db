const password = process.env.MONGO_ADMIN_PASSWORD;
const script = process.env.MONGO_SCRIPT;

if (!password || !script) {
  throw new Error("MONGO_ADMIN_PASSWORD and MONGO_SCRIPT must be set");
}

const admin = db.getSiblingDB("admin");
admin.auth("lab_admin", password);
load(script);
