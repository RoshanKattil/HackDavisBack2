// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ChainCustody {
    struct Material {
        address currentHolder;
        uint256 lastSequence;
        string id;
        string description;
    }

    mapping(string => Material) private materials;
    string[] private materialIds;  // to enumerate

    event MaterialInitialized(string indexed id, address indexed holder);
    event MaterialTransferred(string indexed id, address indexed from, address indexed to, uint256 sequence);

    function initializeMaterial(
        string calldata _id,
        string calldata _description
    ) external {
        require(bytes(materials[_id].id).length == 0, "Already exists");
        materials[_id] = Material(msg.sender, 1, _id, _description);
        materialIds.push(_id);
        emit MaterialInitialized(_id, msg.sender);
    }

    function transferMaterial(string calldata _id, address _newHolder) external {
        Material storage m = materials[_id];
        require(m.currentHolder == msg.sender, "Only holder");
        m.currentHolder = _newHolder;
        m.lastSequence += 1;
        emit MaterialTransferred(_id, msg.sender, _newHolder, m.lastSequence);
    }

    function getMaterial(string calldata _id)
        external
        view
        returns (
            address currentHolder,
            uint256 lastSequence,
            string memory id,
            string memory description
        )
    {
        Material storage m = materials[_id];
        require(bytes(m.id).length != 0, "Not found");
        return (m.currentHolder, m.lastSequence, m.id, m.description);
    }

    function listMaterials() external view returns (string[] memory) {
        return materialIds;
    }
}
