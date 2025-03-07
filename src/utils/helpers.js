module.exports = {
  log: (message) => {
    console.log(`[LOG] ${new Date().toISOString()}: ${message}`);
  },
  error: (message) => {
    console.error(`[ERROR] ${new Date().toISOString()}: ${message}`);
  },
  handleError: (error) => {
    console.error(`[ERROR] ${new Date().toISOString()}: ${error.message}`);
  }
};