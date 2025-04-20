// contracts/scripts/deploy_waste.js
const { ethers } = require("hardhat");

async function main() {
  // grab the first account as deployer/admin
  const [deployer] = await ethers.getSigners();
  console.log("Deploying WasteChain with account:", deployer.address);

  // compile & deploy
  const Waste = await ethers.getContractFactory("WasteChain");
  const waste = await Waste.deploy(deployer.address);
  await waste.deployed();

  console.log("WasteChain deployed to:", waste.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
