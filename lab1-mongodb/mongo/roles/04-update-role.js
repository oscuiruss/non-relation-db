const university = db.getSiblingDB("university");
const removePrivilege = {
  resource: { db: "university", collection: "students" },
  actions: ["remove"]
};

university.grantPrivilegesToRole("studentEditor", [removePrivilege]);
print("Role after adding remove permission:");
printjson(university.getRole("studentEditor", { showPrivileges: true }));

university.revokePrivilegesFromRole("studentEditor", [removePrivilege]);
print("Role after revoking remove permission:");
printjson(university.getRole("studentEditor", { showPrivileges: true }));

