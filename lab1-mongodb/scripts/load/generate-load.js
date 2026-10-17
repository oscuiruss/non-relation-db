const durationSeconds = Number(process.env.LOAD_SECONDS || 120);
const batchSize = Number(process.env.LOAD_BATCH_SIZE || 100);
const collection = db.getSiblingDB("university").load_test;
const deadline = Date.now() + durationSeconds * 1000;
let batch = 0;

collection.createIndex({ batch: 1 });
collection.createIndex({ value: 1 });

print(`Generating load for ${durationSeconds} seconds, batch size ${batchSize}`);

while (Date.now() < deadline) {
  const documents = [];
  for (let i = 0; i < batchSize; i += 1) {
    documents.push({
      batch,
      sequence: i,
      value: Math.random(),
      createdAt: new Date(),
      payload: "mongodb-lab-load"
    });
  }

  collection.insertMany(documents);
  collection.find({ value: { $gte: 0.25, $lte: 0.75 } }).limit(50).toArray();
  collection.updateMany({ batch }, { $inc: { updateCount: 1 } });
  collection.aggregate([
    { $match: { batch: { $gte: Math.max(0, batch - 20) } } },
    { $group: { _id: null, average: { $avg: "$value" } } }
  ]).toArray();

  if (batch > 50 && batch % 5 === 0) {
    collection.deleteMany({ batch: { $lt: batch - 50 } });
  }

  batch += 1;
  if (batch % 20 === 0) {
    print(`Completed batches: ${batch}`);
  }
  sleep(100);
}

print(`Load complete; batches: ${batch}, documents: ${collection.countDocuments()}`);

