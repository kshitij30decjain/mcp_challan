from fastmcp import FastMCP
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from database import db

# Initialize FastMCP server with SSE transport
HOST = "0.0.0.0"
PORT = "8034"

mcp = FastMCP(
    "challan-mcp-server",
    instructions="MCP Server for Samsung Device Challan Management System",
    host=HOST,
    port=int(PORT)
)







@mcp.resource("challan://resources/pending-approvals")
def get_pending_approvals() -> str:
    """
    Get a summary of all pending approvals across different levels.

    Returns:
        JSON string containing counts of pending approvals for manager, HOD, and IT levels.
    """
    pending_manager = db.get_pending_approvals('manager')
    pending_hod = db.get_pending_approvals('hod')
    pending_it = db.get_pending_approvals('it_admin')

    summary = {
        "manager_pending": len(pending_manager),
        "hod_pending": len(pending_hod),
        "it_pending": len(pending_it),
        "total_pending": len(pending_manager) + len(pending_hod) + len(pending_it),
        "last_updated": datetime.now().isoformat()
    }

    return json.dumps(summary, indent=2)


@mcp.resource("challan://resources/all-challans")
def get_all_challans() -> str:
    """
    Get complete list of all challans in the system.

    Returns:
        JSON string containing all challan records with their current status.
    """
    challans = db.get_all_challans()
    return json.dumps(challans, indent=2, default=str)


@mcp.resource("challan://resources/available-devices")
def get_available_devices() -> str:
    """
    Get list of all available Samsung devices that can be requested.

    Returns:
        JSON string containing device types, models, and categories.
    """
    devices = db.get_available_devices()
    return json.dumps(devices, indent=2)


@mcp.resource("challan://resources/challan/{challan_id}")
def get_challan_by_id(challan_id: int) -> str:
    """
    Get detailed information about a specific challan by its ID.

    Args:
        challan_id: The unique identifier of the challan

    Returns:
        JSON string containing complete challan details or error message if not found.
    """
    challan = db.get_challan_status(challan_id)
    if challan:
        return json.dumps(challan, indent=2, default=str)
    else:
        return json.dumps({"error": f"Challan with ID {challan_id} not found"})


@mcp.tool()
def create_challan(
        device_type: str,
        device_model: str,
        serial_number: str,
        quantity: int,
        purpose: str,
        requested_by: str
) -> str:
    """
    Create a new device challan request.

    This tool allows users to submit a new challan request for Samsung devices.
    The request will go through a 3-stage approval process: Manager → HOD → IT Inventory.

    Args:
        device_type: Type of device (phone/tablet)
        device_model: Specific model of the device (e.g., Samsung Galaxy S23 Ultra)
        serial_number: Unique serial number of the device
        quantity: Number of devices being requested
        purpose: Reason for the challan request
        requested_by: Username of the person making the request

    Returns:
        Confirmation message with the new challan ID or error details.
    """
    try:
        # Validate user exists
        user = db.get_user_by_username(requested_by)
        if not user:
            return f"Error: User '{requested_by}' not found. Please provide a valid username."

        # Create challan
        challan_data = {
            "device_type": device_type,
            "device_model": device_model,
            "serial_number": serial_number,
            "quantity": quantity,
            "purpose": purpose,
            "requested_by": requested_by
        }

        challan_id = db.create_challan(challan_data)

        # Send SSE notification for new challan creation
        sse_event = {
            "event": "challan_created",
            "challan_id": challan_id,
            "requested_by": requested_by,
            "device_model": device_model,
            "timestamp": datetime.now().isoformat()
        }

        return f"Challan created successfully! 🎉\n\n" \
               f"Challan ID: {challan_id}\n" \
               f"Device: {device_model}\n" \
               f"Requested by: {requested_by}\n" \
               f"Status: Pending Manager Approval\n\n" \
               f"Your request will now go through the approval workflow:\n" \
               f"1. Manager Approval → 2. HOD Approval → 3. IT Inventory Approval"

    except Exception as e:
        return f"Error creating challan: {str(e)}"


@mcp.tool()
def get_challan_status(challan_id: int) -> str:
    """
    Get the current status and approval progress of a specific challan.

    This tool provides detailed information about where a challan is in the
    approval process, including which levels have approved/rejected and
    any pending actions.

    Args:
        challan_id: The ID of the challan to check

    Returns:
        Detailed status report including approval progress and current stage.
    """
    challan = db.get_challan_status(challan_id)
    if not challan:
        return f" Challan with ID {challan_id} not found."

    # Build status message
    status_message = f" Challan ID: {challan_id}\n"
    status_message += f" Device: {challan['device_model']}\n"
    status_message += f" Requested by: {challan['requested_by']}\n"
    status_message += f" Request date: {challan['request_date']}\n"
    status_message += f" Purpose: {challan['purpose']}\n\n"

    status_message += " Approval Status:\n"
    status_message += f"   • Manager: {challan['manager_status'].upper()}\n"
    if challan['manager_approval_date']:
        status_message += f"     Date: {challan['manager_approval_date']}\n"

    status_message += f"   • HOD: {challan['hod_status'].upper()}\n"
    if challan['hod_approval_date']:
        status_message += f"     Date: {challan['hod_approval_date']}\n"

    status_message += f"   • IT Inventory: {challan['it_status'].upper()}\n"
    if challan['it_approval_date']:
        status_message += f"     Date: {challan['it_approval_date']}\n"

    status_message += f"\n Final Status: {challan['final_status'].upper()}\n"

    if challan['remarks']:
        status_message += f" Remarks: {challan['remarks']}\n"

    # Add progress analysis
    status_message += "\n Progress Analysis:\n"
    if challan['final_status'] == 'approved':
        status_message += "🎉 Fully approved! Device is ready for allocation.\n"
    elif challan['final_status'] == 'rejected':
        if challan['manager_status'] == 'rejected':
            status_message += " Rejected at Manager level.\n"
        elif challan['hod_status'] == 'rejected':
            status_message += " Rejected at HOD level.\n"
        elif challan['it_status'] == 'rejected':
            status_message += " Rejected at IT Inventory level.\n"
    else:
        if challan['manager_status'] == 'pending':
            status_message += " Waiting for Manager approval...\n"
        elif challan['hod_status'] == 'pending':
            status_message += " Waiting for HOD approval...\n"
        elif challan['it_status'] == 'pending':
            status_message += " Waiting for IT Inventory approval...\n"

    return status_message


@mcp.tool()
def approve_challan(challan_id: int, role: str, approver_username: str, remarks: str = None) -> str:
    """
    Approve a challan at the current approval stage.

    This tool allows authorized personnel (Manager, HOD, or IT Admin) to
    approve a challan at their respective level. The system will automatically
    progress the challan to the next stage or mark it as fully approved.

    Args:
        challan_id: The ID of the challan to approve
        role: The role of the approver (manager/hod/it_admin)
        approver_username: Username of the person approving
        remarks: Optional comments about the approval

    Returns:
        Confirmation message with updated status or error details.
    """
    try:
        # Validate challan exists
        challan = db.get_challan_status(challan_id)
        if not challan:
            return f"Error: Challan with ID {challan_id} not found."

        # Validate approver exists and has correct role
        approver = db.get_user_by_username(approver_username)
        if not approver:
            return f"Error: Approver '{approver_username}' not found."

        if approver['role'] != role:
            return f"Error: User '{approver_username}' does not have required role '{role}'."

        # Validate approval workflow order
        if role == 'hod' and challan['manager_status'] != 'approved':
            return "Error: Cannot approve at HOD level before Manager approval."

        if role == 'it_admin' and (challan['manager_status'] != 'approved' or challan['hod_status'] != 'approved'):
            return "Error: Cannot approve at IT level before Manager and HOD approvals."

        # Update approval status
        db.update_approval_status(challan_id, role, 'approved', remarks)

        # Get updated challan status
        updated_challan = db.get_challan_status(challan_id)

        # Send SSE notification for approval
        sse_event = {
            "event": "challan_approved",
            "challan_id": challan_id,
            "approved_by": approver_username,
            "role": role,
            "next_stage": "completed" if role == 'it_admin' else ("hod" if role == 'manager' else "it"),
            "timestamp": datetime.now().isoformat()
        }

        # Build response message
        response = f"Approved successfully!\n\n"
        response += f"Challan ID: {challan_id}\n"
        response += f"Approved by: {approver_username} ({role})\n"

        if role == 'it_admin':
            response += f" Final approval complete! Device is ready for allocation.\n"
        else:
            next_role = "HOD" if role == 'manager' else "IT Inventory"
            response += f"Now waiting for {next_role} approval.\n"

        if remarks:
            response += f" Remarks: {remarks}\n"

        return response

    except Exception as e:
        return f"Error approving challan: {str(e)}"


@mcp.tool()
def reject_challan(challan_id: int, role: str, rejecter_username: str, rejection_reason: str) -> str:
    """
    Reject a challan at the current approval stage.

    This tool allows authorized personnel to reject a challan with a required
    reason. Rejection at any stage stops the approval process immediately.

    Args:
        challan_id: The ID of the challan to reject
        role: The role of the rejecter (manager/hod/it_admin)
        rejecter_username: Username of the person rejecting
        rejection_reason: Mandatory reason for rejection

    Returns:
        Confirmation message with rejection details or error message.
    """
    try:
        # Validate challan exists
        challan = db.get_challan_status(challan_id)
        if not challan:
            return f"Error: Challan with ID {challan_id} not found."

        # Validate rejecter exists and has correct role
        rejecter = db.get_user_by_username(rejecter_username)
        if not rejecter:
            return f"Error: Rejecter '{rejecter_username}' not found."

        if rejecter['role'] != role:
            return f"Error: User '{rejecter_username}' does not have required role '{role}'."

        # Update rejection status
        db.update_approval_status(challan_id, role, 'rejected', rejection_reason)

        # Send SSE notification for rejection
        sse_event = {
            "event": "challan_rejected",
            "challan_id": challan_id,
            "rejected_by": rejecter_username,
            "role": role,
            "reason": rejection_reason,
            "timestamp": datetime.now().isoformat()
        }

        return f" Challan rejected successfully!\n\n" \
               f"Challan ID: {challan_id}\n" \
               f"Rejected by: {rejecter_username} ({role})\n" \
               f"Reason: {rejection_reason}\n\n" \
               f"The approval process has been stopped. " \
               f"The requester may need to submit a new request with updated information."

    except Exception as e:
        return f"Error rejecting challan: {str(e)}"


@mcp.tool()
def list_my_challans(username: str) -> str:
    """
    List all challans created by a specific user.

    This tool allows users to view their own challan requests and track
    their progress through the approval workflow.

    Args:
        username: The username to filter challans by

    Returns:
        List of challans created by the user with their current status.
    """
    try:
        # Validate user exists
        user = db.get_user_by_username(username)
        if not user:
            return f"Error: User '{username}' not found."

        challans = db.get_all_challans(username)

        if not challans:
            return f"No challans found for user '{username}'."

        response = f" Challans for {username}:\n\n"

        for i, challan in enumerate(challans, 1):
            response += f"{i}. Challan ID: {challan['id']}\n"
            response += f"   Device: {challan['device_model']}\n"
            response += f"   Status: {challan['final_status'].upper()}\n"
            response += f"   Requested: {challan['request_date']}\n"

            # Show current stage if pending
            if challan['final_status'] == 'pending':
                if challan['manager_status'] == 'pending':
                    response += f"    Waiting for Manager approval\n"
                elif challan['hod_status'] == 'pending':
                    response += f"    Waiting for HOD approval\n"
                elif challan['it_status'] == 'pending':
                    response += f"    Waiting for IT approval\n"

            response += "\n"

        response += f"Total: {len(challans)} challan(s)"
        return response

    except Exception as e:
        return f"Error retrieving challans: {str(e)}"


@mcp.tool()
def get_pending_approvals_for_role(role: str, username: str) -> str:
    """
    Get list of challans pending approval for a specific role.

    This tool helps managers, HODs, and IT admins see what challans
    are waiting for their approval.

    Args:
        role: The role to check pending approvals for (manager/hod/it_admin)
        username: Username of the person checking (for validation)

    Returns:
        List of challans pending approval at the specified level.
    """
    try:
        # Validate user exists and has correct role
        user = db.get_user_by_username(username)
        if not user:
            return f"Error: User '{username}' not found."

        if user['role'] != role:
            return f"Error: User '{username}' does not have required role '{role}'."

        pending_challans = db.get_pending_approvals(role)

        if not pending_challans:
            return f"No challans pending {role} approval."

        response = f"⏳ Challans pending {role.upper()} approval:\n\n"

        for i, challan in enumerate(pending_challans, 1):
            response += f"{i}. Challan ID: {challan['id']}\n"
            response += f"   Device: {challan['device_model']}\n"
            response += f"   Requested by: {challan['requested_by']}\n"
            response += f"   Purpose: {challan['purpose']}\n"
            response += f"   Requested: {challan['request_date']}\n\n"

        response += f"Total pending: {len(pending_challans)}"
        return response

    except Exception as e:
        return f"Error retrieving pending approvals: {str(e)}"


@mcp.tool()
def get_available_samsung_devices() -> str:
    """
    Get complete list of available Samsung devices for challan requests.

    Returns:
        List of all Samsung device models categorized by type with descriptions.
    """
    try:
        devices = db.get_available_devices()

        if not devices:
            return "No devices available in the database."

        response = "📱 Available Samsung Devices:\n\n"

        # Group by device type
        devices_by_type = {}
        for device in devices:
            if device['device_type'] not in devices_by_type:
                devices_by_type[device['device_type']] = []
            devices_by_type[device['device_type']].append(device)

        for device_type, type_devices in devices_by_type.items():
            response += f"#{device_type.upper()}S:\n"
            for device in type_devices:
                response += f"  • {device['device_model']} ({device['category']})\n"
            response += "\n"

        response += f"Total devices: {len(devices)} models"
        return response

    except Exception as e:
        return f"Error retrieving devices: {str(e)}"


if __name__ == "__main__":
    # Run the FastMCP server with SSE transport
    mcp.run(transport="sse")