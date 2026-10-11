const admin = db.getSiblingDB("admin");
const users = [
  { user: "backup_user", password: process.env.BACKUP_PASSWORD, role: "backup" },
  { user: "restore_user", password: process.env.RESTORE_PASSWORD, role: "restore" }
];

for (const item of users) {
  if (!item.password) {
    throw new Error(`Password environment variable is missing for ${item.user}`);
  }
  const roles = [{ role: item.role, db: "admin" }];
  if (admin.getUser(item.user)) {
    admin.updateUser(item.user, { pwd: item.password, roles });
    print(`Updated user ${item.user}`);
  } else {
    admin.createUser({ user: item.user, pwd: item.password, roles });
    print(`Created user ${item.user}`);
  }
}

