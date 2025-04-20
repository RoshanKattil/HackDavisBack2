async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying with", deployer.address);
    const C = await ethers.getContractFactory("ChainCustody");
    const c = await C.deploy();
    await c.deployed();
    console.log("ChainCustody deployed to:", c.address);
  }
  main().catch(err => {
    console.error(err);
    process.exit(1);
  });
  