const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Memulai deployment EVotingBlockchain...");

  const [deployer] = await hre.ethers.getSigners();
  const factory = await hre.ethers.getContractFactory("EVotingBlockchain");
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const deployTx = contract.deploymentTransaction();
  const receipt = await deployTx.wait();
  const network = await hre.ethers.provider.getNetwork();

  const data = {
    contractName: "EVotingBlockchain",
    address,
    network: hre.network.name,
    chainId: Number(network.chainId),
    rpcUrl: "http://127.0.0.1:8545",
    deployer: deployer.address,
    deployTxHash: deployTx.hash,
    deployBlock: receipt.blockNumber,
    deployedAt: new Date().toISOString(),
  };

  const outPath = process.env.DEPLOYMENT_FILE || path.join(__dirname, "..", "deployment.json");
  fs.writeFileSync(outPath, JSON.stringify(data, null, 2));

  console.log("Deployment berhasil.");
  console.log("Alamat kontrak :", address);
  console.log("Deployer       :", deployer.address, "(otomatis menjadi Panitia pertama)");
  console.log("Tersimpan di deployment.json");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
