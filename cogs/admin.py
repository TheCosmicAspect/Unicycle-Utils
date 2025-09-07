from discord.ext import commands
import discord
from discord import app_commands
from models.database import Session, AdminRole

class AdminCommands(commands.Cog):
    """Commands for managing unicycle admin roles"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(role="The role to add as an admin role")
    async def add_admin_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        """Add a role as a unicycle admin role"""
        print(f"\nProcessing add_admin_role command:")
        print(f"User: {interaction.user} (ID: {interaction.user.id})")
        print(f"Guild ID from interaction: {interaction.guild_id}")
        
        try:
            if not interaction.guild_id:
                print("No guild ID available")
                await interaction.response.send_message("Could not verify guild context. Please try again.", ephemeral=True)
                return
                
            # Get the guild directly from the bot
            guild = self.bot.get_guild(interaction.guild_id)
            print(f"Guild from get_guild: {guild}")
            
            if not guild:
                print("Guild not in cache, fetching...")
                guild = await self.bot.fetch_guild(interaction.guild_id)
                print(f"Guild from fetch_guild: {guild}")
            
            print(f"Final guild object: {guild}")
            print(f"Guild owner ID: {guild.owner_id}")
            
            # Get the member object
            member = guild.get_member(interaction.user.id)
            if not member:
                print("Member not in cache, fetching...")
                member = await guild.fetch_member(interaction.user.id)
            
            print(f"Member object: {member}")
            print(f"Member permissions: {member.guild_permissions}")
            
        except Exception as e:
            print(f"Error during guild/member fetch: {e}")
            await interaction.response.send_message("An error occurred while verifying permissions. Please try again.", ephemeral=True)
            return
            
        if not guild or not member:
            print("Could not get guild or member context")
            await interaction.response.send_message("Could not verify permissions. Please try again.", ephemeral=True)
            return

        # Check permissions
        if guild.owner_id == member.id or member.guild_permissions.administrator:
            print("User has required permissions")
            print(f"Is Owner: {guild.owner_id == member.id}")
            print(f"Is Admin: {member.guild_permissions.administrator}")
            
            # Add the admin role to the database here
            print("Permission check passed - proceeding with adding admin role")
            await interaction.response.send_message(f"Added {role.name} as an admin role.", ephemeral=True)
        else:
            print("User lacks required permissions")
            print(f"Guild Owner ID: {guild.owner_id}")
            print(f"User ID: {member.id}")
            print(f"Is Owner: {guild.owner_id == member.id}")
            print(f"Admin Permission: {member.guild_permissions.administrator}")
            print(f"All Permissions: {member.guild_permissions}")
            await interaction.response.send_message("Only server administrators can add admin roles!", ephemeral=True)

        session = Session()
        try:
            existing = session.query(AdminRole).filter_by(role_id=str(role.id)).first()
            if existing:
                await interaction.response.send_message(f"Role {role.mention} is already an admin role!", ephemeral=True)
                return

            admin_role = AdminRole(role_id=str(role.id))
            session.add(admin_role)
            session.commit()
            await interaction.response.send_message(f"Added {role.mention} as an admin role.", ephemeral=True)
        except Exception as e:
            print(f"Error adding admin role: {e}")
            await interaction.response.send_message("Failed to add admin role.", ephemeral=True)
        finally:
            session.close()

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(role="The role to remove from admin roles")
    async def remove_admin_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        """Remove a role from unicycle admin roles"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Could not verify your permissions.", ephemeral=True)
            return

        if not (interaction.guild.owner_id == interaction.user.id or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("Only server administrators can remove admin roles!", ephemeral=True)
            return

        session = Session()
        try:
            admin_role = session.query(AdminRole).filter_by(role_id=str(role.id)).first()
            if not admin_role:
                await interaction.response.send_message(f"Role {role.mention} is not an admin role!", ephemeral=True)
                return

            session.delete(admin_role)
            session.commit()
            await interaction.response.send_message(f"Removed {role.mention} from admin roles.", ephemeral=True)
        except Exception as e:
            print(f"Error removing admin role: {e}")
            await interaction.response.send_message("Failed to remove admin role.", ephemeral=True)
        finally:
            session.close()

    @app_commands.command()
    @app_commands.guild_only()
    async def list_admin_roles(self, interaction: discord.Interaction) -> None:
        """List all unicycle admin roles"""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return

        session = Session()
        try:
            admin_roles = session.query(AdminRole).all()
            if not admin_roles:
                await interaction.response.send_message("No admin roles are configured.", ephemeral=True)
                return

            roles_text = []
            for admin_role in admin_roles:
                role = interaction.guild.get_role(int(str(admin_role.role_id)))
                if role:
                    roles_text.append(role.mention)

            if not roles_text:
                await interaction.response.send_message("No valid admin roles found.", ephemeral=True)
                return

            embed = discord.Embed(
                title="Unicycle Admin Roles",
                description="\n".join(roles_text),
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error listing admin roles: {e}")
            await interaction.response.send_message("Failed to list admin roles.", ephemeral=True)
        finally:
            session.close()

async def setup(bot: commands.Bot) -> None:
    """Add the cog to the bot"""
    await bot.add_cog(AdminCommands(bot))