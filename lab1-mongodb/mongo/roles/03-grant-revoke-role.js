const university = db.getSiblingDB("university");

university.grantRolesToUser("student_reader", [
  { role: "studentEditor", db: "university" }
]);
print("After grant:");
printjson(university.getUser("student_reader"));

university.revokeRolesFromUser("student_reader", [
  { role: "studentEditor", db: "university" }
]);
print("After revoke:");
printjson(university.getUser("student_reader"));

