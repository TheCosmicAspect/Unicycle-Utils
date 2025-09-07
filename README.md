# Unicycle Tracker Discord Bot

A Discord bot for tracking and managing unicycles, including ownership and custody tracking.

**Add to your server with [this link](https://discord.com/api/oauth2/authorize?client_id=1413756668512178278&permissions=268438528&scope=bot%20applications.commands) **

### Commands

- `/add_admin_role`: Designates a role as a "Unicycle admin role". Users with this role get universal edit privileges, not just on unicycles they own.
- `/add-unicycle`: Add a Unicycle with specified name and description. Default owner is user who called the command.
- `/edit-unicycle`: Opens *name*, *description*, *owner*, and *is_club_owned* up for edits via given parameters.
- `/list_admin_roles`: Lists the roles that function as "Unicycle admin roles".
- `/list-unicycles`: Lists all unicycles with optional parameters to filter by.
- `/remove_admin_role`: Removes a role from list of "Unicycle admin roles".
- `/remove-unicycle`: Removes the specified unicycle. Requires the user to manually confirm.
- `/transfer-unicycle`: Transfers custody of a unicycle to specified user. This exchanged must be accepted by the target or an admin.
- `/view-unicycle`: See details about specified unicycle

### Permissions

- Server administrators can manage admin roles
- Unicycle admin roles can:
  - Edit any unicycle
  - Transfer any unicycle
  - Accept/decline any transfer
- Regular users can:
  - Add their own unicycles
  - Edit their own unicycles
  - Transfer unicycles in their custody
  - View any unicycle's details
