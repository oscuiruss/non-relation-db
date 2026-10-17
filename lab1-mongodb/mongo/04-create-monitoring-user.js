const admin = db.getSiblingDB("admin");
const password = process.env.MONITORING_PASSWORD || passwordPrompt();
const roles = [
  { role: "clusterMonitor", db: "admin" },
  { role: "read", db: "local" }
];

if (admin.getUser("mongodb_exporter")) {
  admin.updateUser("mongodb_exporter", { pwd: password, roles });
  print("Updated monitoring user mongodb_exporter");
} else {
  admin.createUser({ user: "mongodb_exporter", pwd: password, roles });
  print("Created monitoring user mongodb_exporter");
}
