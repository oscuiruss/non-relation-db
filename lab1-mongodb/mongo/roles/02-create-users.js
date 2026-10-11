const university = db.getSiblingDB("university");

const users = [
  { user: "student_reader", password: process.env.READER_PASSWORD, role: "universityReader" },
  { user: "student_editor", password: process.env.EDITOR_PASSWORD, role: "studentEditor" },
  { user: "grades_reader", password: process.env.GRADES_PASSWORD, role: "gradesOnlyReader" },
  { user: "temporary_user", password: process.env.TEMP_PASSWORD, role: "temporaryRole" }
];

for (const item of users) {
  if (!item.password) {
    throw new Error(`Password environment variable is missing for ${item.user}`);
  }

  const roles = [{ role: item.role, db: "university" }];
  if (university.getUser(item.user)) {
    university.updateUser(item.user, { pwd: item.password, roles });
    print(`Updated user ${item.user}`);
  } else {
    university.createUser({ user: item.user, pwd: item.password, roles });
    print(`Created user ${item.user}`);
  }
}

printjson(university.getUsers());

