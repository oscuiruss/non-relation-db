const university = db.getSiblingDB("university");

if (university.getUser("temporary_user")) {
  university.dropUser("temporary_user");
  print("Deleted user temporary_user");
} else {
  print("User temporary_user is already absent");
}

if (university.getRole("temporaryRole")) {
  university.dropRole("temporaryRole");
  print("Deleted role temporaryRole");
} else {
  print("Role temporaryRole is already absent");
}

