// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/AccessControl.sol";

contract WasteChain is AccessControl {
    bytes32 public constant GENERATOR   = keccak256("GENERATOR");
    bytes32 public constant TRANSPORTER = keccak256("TRANSPORTER");
    bytes32 public constant DISPOSER    = keccak256("DISPOSER");

    enum Status { Created, InTransit, Delivered, Disposed }

    struct WasteRecord {
        address currentHolder;
        Status  status;
        string  wasteType;      // e.g. "Lead‑acid batteries"
        string  hazardClass;    // e.g. "Class 8 corrosive"
        uint256 quantity;       // in `units`
        string  units;          // e.g. "kg", "L"
        uint256 sequence;
    }

    mapping(string => WasteRecord) private records;

    // Events for on‑chain audit
    event Created(string indexed wasteId, address indexed generator);
    event Transferred(string indexed wasteId, address indexed from, address indexed to);
    event StatusChanged(string indexed wasteId, Status status);

    constructor(address admin) {
    // grant the DEFAULT_ADMIN_ROLE to your admin address
    _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function registerGenerator(address addr) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(GENERATOR, addr);
    }
    function registerTransporter(address addr) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(TRANSPORTER, addr);
    }
    function registerDisposer(address addr) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(DISPOSER, addr);
    }

    function createWaste(
        string calldata wasteId,
        string calldata wasteType,
        string calldata hazardClass,
        uint256       quantity,
        string calldata units
    )
        external
        onlyRole(GENERATOR)
    {
        require(records[wasteId].sequence == 0, "Already exists");
        records[wasteId] = WasteRecord({
            currentHolder: msg.sender,
            status:        Status.Created,
            wasteType:     wasteType,
            hazardClass:   hazardClass,
            quantity:      quantity,
            units:         units,
            sequence:      1
        });
        emit Created(wasteId, msg.sender);
    }

    function transferWaste(string calldata wasteId, address to)
        external
        onlyRole(TRANSPORTER)
    {
        WasteRecord storage w = records[wasteId];
        require(w.currentHolder == msg.sender, "Not current holder");
        require(w.status == Status.Created || w.status == Status.Delivered, "Invalid status");
        w.currentHolder = to;
        w.status = Status.InTransit;
        w.sequence += 1;
        emit Transferred(wasteId, msg.sender, to);
        emit StatusChanged(wasteId, w.status);
    }

    function deliverWaste(string calldata wasteId)
        external
        onlyRole(TRANSPORTER)
    {
        WasteRecord storage w = records[wasteId];
        require(w.currentHolder == msg.sender, "Not in transit");
        require(w.status == Status.InTransit, "Not in transit");
        w.status = Status.Delivered;
        w.sequence += 1;
        emit StatusChanged(wasteId, w.status);
    }

    function disposeWaste(string calldata wasteId)
        external
        onlyRole(DISPOSER)
    {
        WasteRecord storage w = records[wasteId];
        require(w.currentHolder == msg.sender, "Must be disposer");
        require(w.status == Status.Delivered, "Not delivered yet");
        w.status = Status.Disposed;
        w.sequence += 1;
        emit StatusChanged(wasteId, w.status);
    }

    function getWaste(string calldata wasteId)
        external
        view
        returns (
            address currentHolder,
            Status  status,
            string memory wasteType,
            string memory hazardClass,
            uint256 quantity,
            string memory units,
            uint256 sequence
        )
    {
        WasteRecord storage w = records[wasteId];
        return (
            w.currentHolder,
            w.status,
            w.wasteType,
            w.hazardClass,
            w.quantity,
            w.units,
            w.sequence
        );
    }
}
