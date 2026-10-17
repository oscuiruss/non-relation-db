const university = db.getSiblingDB("university");
const library = db.getSiblingDB("library");

university.students.drop();
university.grades.drop();
university.courses.drop();
library.books.drop();
library.loans.drop();

university.students.insertMany([
  { studentId: 1, name: "Иван Иванов", group: "М01-601", active: true },
  { studentId: 2, name: "Анна Петрова", group: "М01-601", active: true },
  { studentId: 3, name: "Мария Сидорова", group: "М01-602", active: true }
]);
university.students.createIndex({ studentId: 1 }, { unique: true });

university.grades.insertMany([
  { studentId: 1, subject: "Databases", grade: 5 },
  { studentId: 2, subject: "Databases", grade: 4 },
  { studentId: 3, subject: "Databases", grade: 5 }
]);
university.grades.createIndex({ studentId: 1, subject: 1 }, { unique: true });

university.courses.insertMany([
  { code: "DB101", name: "Databases" },
  { code: "OS101", name: "Operating Systems" }
]);

library.books.insertMany([
  { isbn: "978-1", title: "MongoDB Basics", available: true },
  { isbn: "978-2", title: "Linux Administration", available: true }
]);
library.books.createIndex({ isbn: 1 }, { unique: true });
library.loans.insertOne({ isbn: "978-1", studentId: 1, returned: false });

print(`university.students: ${university.students.countDocuments()}`);
print(`university.grades: ${university.grades.countDocuments()}`);
print(`library.books: ${library.books.countDocuments()}`);

