const university = db.getSiblingDB("university");

function upsertRole(name, definition) {
  if (university.getRole(name)) {
    university.updateRole(name, definition);
    print(`Updated role ${name}`);
  } else {
    university.createRole({ role: name, ...definition });
    print(`Created role ${name}`);
  }
}

upsertRole("universityReader", {
  privileges: [
    {
      resource: { db: "university", collection: "" },
      actions: ["find", "listCollections", "listIndexes"]
    }
  ],
  roles: []
});

upsertRole("studentEditor", {
  privileges: [
    {
      resource: { db: "university", collection: "students" },
      actions: ["find", "insert", "update"]
    }
  ],
  roles: []
});

upsertRole("gradesOnlyReader", {
  privileges: [
    {
      resource: { db: "university", collection: "grades" },
      actions: ["find"]
    }
  ],
  roles: []
});

upsertRole("temporaryRole", {
  privileges: [
    {
      resource: { db: "university", collection: "courses" },
      actions: ["find"]
    }
  ],
  roles: []
});

printjson(university.getRoles({ showPrivileges: true }));

