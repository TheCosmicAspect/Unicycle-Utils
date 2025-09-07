import discord
from discord import app_commands
from discord.ext import commands
from models.database import Session, Unicycle, AdminRole, get_next_guild_id

class UnicycleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_transfers = {}  # Store pending transfer requests

    async def unicycle_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[int]]:
        """Autocomplete for unicycle IDs, filtering by name or ID"""
        if not interaction.guild_id:
            return []
            
        session = Session()
        try:
            # Filter unicycles by guild_id
            unicycles = session.query(Unicycle).filter_by(guild_id=str(interaction.guild_id)).all()
            choices = []
            
            # Convert current to lowercase for case-insensitive comparison
            current_lower = current.lower() if current else ""
            
            for unicycle in unicycles:
                # Use guild-specific ID for display and value
                display_id = unicycle.guild_specific_id
                name = unicycle.name_str
                display_name = f"#{display_id}: {name}"
                
                # Match if the current input is empty or matches either the ID or name
                if (not current or 
                    current_lower in display_name.lower() or 
                    (current.isdigit() and str(display_id).startswith(current))):
                    # Use the guild-specific ID as the value
                    choices.append(app_commands.Choice(name=display_name, value=display_id))
            
            return choices[:25]  # Discord limits to 25 choices
        except Exception as e:
            print(f"Error in unicycle_autocomplete: {e}")
            return []
        finally:
            session.close()

    async def is_admin(self, interaction: discord.Interaction, session) -> bool:
        # Check guild context
        if not interaction.guild:
            return False

        # Fetch the member to get proper permissions and roles
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(interaction.user.id)
            except discord.NotFound:
                return False

        # Check if user is server owner or administrator
        if interaction.guild.owner_id == member.id or member.guild_permissions.administrator:
            return True
        
        # Check admin roles for this guild
        user_role_ids = [str(role.id) for role in member.roles]
        admin_roles = session.query(AdminRole.role_id).filter_by(guild_id=str(interaction.guild_id)).all()
        return any(str(role_id) in user_role_ids for (role_id,) in admin_roles)

    @app_commands.command(name="add-unicycle", description="Add a new unicycle to the tracker")
    async def add_unicycle(self, interaction: discord.Interaction, name: str, description: str):
        # Debug statements:
        print(f"add_unicycle called by user {interaction.user.id} in guild {interaction.guild_id} with name '{name}' and description '{description}'")

        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return
            
        session = Session()
        try:
            # Check if a unicycle with this name already exists in this guild
            existing = session.query(Unicycle).filter_by(
                guild_id=str(interaction.guild_id),
                name=name
            ).first()
            
            if existing:
                await interaction.response.send_message(
                    f"A unicycle named '{name}' already exists in this server!", 
                    ephemeral=True
                )
                return
            
            # Get the next guild-specific ID
            guild_id = str(interaction.guild_id)
            next_id = get_next_guild_id(session, guild_id)
            
            unicycle = Unicycle(
                guild_id=guild_id,
                guild_specific_id=next_id,
                name=name,
                description=description,
                owner_id=str(interaction.user.id),
                custody_id=str(interaction.user.id)
            )
            session.add(unicycle)
            session.commit()
            await interaction.response.send_message(f"Unicycle '{name}' has been added!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error adding unicycle: {str(e)}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="transfer-unicycle", description="Transfer custody of a unicycle to another user")
    @app_commands.describe(unicycle_id="The unicycle number (as shown in the list)")
    @app_commands.autocomplete(unicycle_id=unicycle_autocomplete)
    async def transfer_unicycle(self, interaction: discord.Interaction, unicycle_id: int, user: discord.Member):
        # Debug statements:
        print(f"transfer_unicycle called by user {interaction.user.id} in guild {interaction.guild_id} with unicycle_id {unicycle_id} and user {user.id}")

        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return
            
        session = Session()
        try:
            # Filter by both guild-specific ID and guild_id
            unicycle = session.query(Unicycle).filter_by(
                guild_specific_id=unicycle_id,
                guild_id=str(interaction.guild_id)
            ).first()
            
            if not unicycle:
                await interaction.response.send_message("Unicycle not found in this server!", ephemeral=True)
                return

            # Check if user has permission to transfer
            if not (str(interaction.user.id) == unicycle.custody_id or await self.is_admin(interaction, session)):
                await interaction.response.send_message("You don't have permission to transfer this unicycle!", ephemeral=True)
                return

            # Create transfer request
            self.pending_transfers[unicycle_id] = {
                'from_user': interaction.user.id,
                'to_user': user.id
            }

            # Create confirmation buttons
            outer_self = self  # Store reference to outer class
            unicycle_id_str = str(unicycle.id)  # Store ID as string
            
            class ConfirmButtons(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=300)  # 5 minute timeout

                @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
                async def accept(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # Create a new session for the button interaction
                    button_session = Session()
                    try:
                        # Get the current state of the unicycle
                        current_unicycle = button_session.query(Unicycle).filter_by(id=int(unicycle_id_str)).first()
                        if not current_unicycle:
                            await button_interaction.response.send_message("Unicycle not found!", ephemeral=True)
                            return

                        if button_interaction.user.id == user.id or await outer_self.is_admin(button_interaction, button_session):
                            # Get the unicycle values before modifying
                            unicycle_name = current_unicycle.name_str
                            # Update the custody
                            current_unicycle.set_custody_id(str(user.id))
                            button_session.commit()
                            await button_interaction.response.send_message(
                                f"Transfer of '{unicycle_name}' to {user.mention} complete!", 
                                ephemeral=True
                            )
                            self.stop()
                        else:
                            await button_interaction.response.send_message("You cannot accept this transfer!", ephemeral=True)
                    finally:
                        button_session.close()

                @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
                async def decline(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    button_session = Session()
                    try:
                        current_unicycle = button_session.query(Unicycle).filter_by(id=int(unicycle_id_str)).first()
                        if not current_unicycle:
                            await button_interaction.response.send_message("Unicycle not found!", ephemeral=True)
                            return

                        if button_interaction.user.id == user.id or await outer_self.is_admin(button_interaction, button_session):
                            await button_interaction.response.send_message(
                                f"Transfer of '{current_unicycle.name_str}' declined.", 
                                ephemeral=True
                            )
                            self.stop()
                        else:
                            await button_interaction.response.send_message("You cannot decline this transfer!", ephemeral=True)
                    finally:
                        button_session.close()

            view = ConfirmButtons()
            await interaction.response.send_message(
                f"{user.mention}, {interaction.user.mention} wants to transfer '{unicycle.name}' to you. Do you accept?",
                view=view
            )

        except Exception as e:
            await interaction.response.send_message(f"Error transferring unicycle: {str(e)}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="view-unicycle", description="View details of a specific unicycle")
    @app_commands.describe(unicycle_id="The unicycle number (as shown in the list)")
    @app_commands.autocomplete(unicycle_id=unicycle_autocomplete)
    async def view_unicycle(self, interaction: discord.Interaction, unicycle_id: int):
        # Debug statements:
        print(f"view_unicycle called by user {interaction.user.id} in guild {interaction.guild_id} with unicycle_id {unicycle_id}")

        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return
            
        session = Session()
        try:
            # Get the unicycle by its guild-specific ID
            unicycle = session.query(Unicycle).filter_by(
                guild_specific_id=unicycle_id,
                guild_id=str(interaction.guild_id)
            ).first()
            
            if not unicycle:
                await interaction.response.send_message("Unicycle not found in this server!", ephemeral=True)
                return

            owner = await self.bot.fetch_user(int(unicycle.owner_id_str)) if unicycle.owner_id_str != "Club" else "Club"
            custody = await self.bot.fetch_user(int(unicycle.custody_id_str))
            
            embed = discord.Embed(title=unicycle.name_str, description=unicycle.description_str, color=discord.Color.blue())
            embed.add_field(name="Owner", value=str(owner), inline=True)
            embed.add_field(name="Current Custody", value=custody.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error viewing unicycle: {str(e)}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="list-unicycles", description="List unicycles in this server with optional filters")
    @app_commands.describe(
        owner="Filter by owner (mention a user)",
        club_owned="Show only club-owned unicycles",
        in_custody_of="Filter by who has custody (mention a user)",
        search_text="Filter by text in name or description",
        show_all="Show all unicycles, even if filters are set (admin only)"
    )
    async def list_unicycles(
        self, 
        interaction: discord.Interaction,
        owner: discord.Member | None = None,
        club_owned: bool = False,
        in_custody_of: discord.Member | None = None,
        search_text: str | None = None,
        show_all: bool = False
    ):
        # Debug statements:
        print(f"list_unicycles called by user {interaction.user.id} in guild {interaction.guild_id} with filters: owner={owner}, club_owned={club_owned}, in_custody_of={in_custody_of}, search_text='{search_text}', show_all={show_all}")

        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return
            
        session = Session()
        try:
            from sqlalchemy import or_, and_, not_
            
            # Start with base query filtered by guild
            query = session.query(Unicycle).filter_by(guild_id=str(interaction.guild_id))
            
            # Track active filters for the embed title
            filters = []
            
            # Apply filters (unless show_all is True and user is admin)
            if show_all and await self.is_admin(interaction, session):
                filters.append("showing all")
            else:
                if owner:
                    query = query.filter_by(owner_id=str(owner.id))
                    filters.append(f"owned by {owner.display_name}")
                    
                if club_owned:
                    query = query.filter_by(owner_id="Club")
                    filters.append("club-owned")
                elif not owner:  # Only apply this if no specific owner was requested
                    # Only show non-club unicycles
                    query = query.filter(Unicycle.__table__.c.owner_id != "Club")
                    
                if in_custody_of:
                    query = query.filter_by(custody_id=str(in_custody_of.id))
                    filters.append(f"in custody of {in_custody_of.display_name}")
                    
                if search_text:
                    search_pattern = f"%{search_text}%"
                    query = query.filter(
                        or_(
                            Unicycle.__table__.c.name.like(search_pattern),
                            Unicycle.__table__.c.description.like(search_pattern)
                        )
                    )
                    filters.append(f'matching "{search_text}"')
            
            # Get filtered results
            unicycles = query.order_by(Unicycle.guild_specific_id).all()
            
            if not unicycles:
                await interaction.response.send_message(
                    "No unicycles found matching your filters!", 
                    ephemeral=True
                )
                return

            # Create embed title based on filters
            title = "Unicycles"
            if filters:
                title += f" ({', '.join(filters)})"
                
            embed = discord.Embed(title=title, color=discord.Color.blue())
            
            for unicycle in unicycles:
                # Get owner information
                owner_display = "Club"
                if unicycle.owner_id_str != "Club":
                    try:
                        owner_user = await self.bot.fetch_user(int(unicycle.owner_id_str))
                        owner_display = str(owner_user)
                    except:
                        owner_display = f"Unknown User ({unicycle.owner_id_str})"
                
                # Get custody information
                try:
                    custody = await self.bot.fetch_user(int(unicycle.custody_id_str))
                    custody_display = custody.mention
                except:
                    custody_display = f"Unknown User ({unicycle.custody_id_str})"
                
                # Format the field value with ownership and custody info
                field_value = []
                field_value.append(f"Owner: {owner_display}")
                field_value.append(f"Custody: {custody_display}")
                if unicycle.description_str:
                    field_value.append(f"Description: {unicycle.description_str}")
                
                embed.add_field(
                    name=f"#{unicycle.guild_specific_id}: {unicycle.name_str}",
                    value="\n".join(field_value),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error listing unicycles: {str(e)}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="remove-unicycle", description="Remove a unicycle from the tracker")
    @app_commands.describe(
        unicycle_id="The unicycle number to remove",
        confirm="Type 'confirm' to verify you want to remove this unicycle"
    )
    @app_commands.autocomplete(unicycle_id=unicycle_autocomplete)
    async def remove_unicycle(
        self,
        interaction: discord.Interaction,
        unicycle_id: int,
        confirm: str
    ):
        # Debug statements:
        print(f"remove_unicycle called by user {interaction.user.id} in guild {interaction.guild_id} with unicycle_id {unicycle_id} and confirm '{confirm}'")

        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return
            
        if confirm.lower() != "confirm":
            await interaction.response.send_message(
                "Please type 'confirm' to verify you want to remove this unicycle.", 
                ephemeral=True
            )
            return
            
        session = Session()
        try:
            # Get the unicycle by its guild-specific ID
            unicycle = session.query(Unicycle).filter_by(
                guild_specific_id=unicycle_id,
                guild_id=str(interaction.guild_id)
            ).first()
            
            if not unicycle:
                await interaction.response.send_message(
                    f"Unicycle #{unicycle_id} not found in this server!", 
                    ephemeral=True
                )
                return
                
            # Check if user has permission to remove this unicycle
            is_owner = str(interaction.user.id) == unicycle.owner_id_str
            is_admin = await self.is_admin(interaction, session)
            
            if not (is_owner or is_admin):
                await interaction.response.send_message(
                    "You don't have permission to remove this unicycle! Only the owner or admins can remove it.", 
                    ephemeral=True
                )
                return
            
            # Store unicycle details for the confirmation message
            unicycle_name = unicycle.name_str
            
            # Remove the unicycle
            session.delete(unicycle)
            session.commit()
            
            await interaction.response.send_message(
                f"Successfully removed unicycle #{unicycle_id}: {unicycle_name}", 
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"Error removing unicycle: {str(e)}", 
                ephemeral=True
            )
        finally:
            session.close()

    @app_commands.command(name="edit-unicycle", description="Edit a unicycle's details")
    @app_commands.describe(
        unicycle_id="The unicycle number (as shown in the list)",
        name="The new name for the unicycle (optional)",
        description="The new description for the unicycle (optional)",
        owner="The new owner of the unicycle (@ mention a user or type 'club' for Club ownership)",
        is_club_owned="Set to True to make this a club-owned unicycle"
    )
    @app_commands.autocomplete(unicycle_id=unicycle_autocomplete)
    async def edit_unicycle(
        self, 
        interaction: discord.Interaction, 
        unicycle_id: int, 
        name: str | None = None, 
        description: str | None = None,
        owner: discord.Member | None = None,
        is_club_owned: bool = False
    ):
        # Debug statements:
        print(f"edit_unicycle called by user {interaction.user.id} in guild {interaction.guild_id} with unicycle_id {unicycle_id}, name '{name}', description '{description}', owner '{owner}', is_club_owned {is_club_owned}")

        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return
            
        session = Session()
        try:
            # Check that the unicycle exists and belongs to this guild
            unicycle = session.query(Unicycle).filter_by(
                guild_specific_id=unicycle_id,
                guild_id=str(interaction.guild_id)
            ).first()
            
            if not unicycle:
                await interaction.response.send_message(
                    "Unicycle not found in this server!", 
                    ephemeral=True
                )
                return
                
            # If changing the name, check it's not duplicate in this guild
            if name is not None and name != unicycle.name_str:
                existing = session.query(Unicycle).filter_by(
                    guild_id=str(interaction.guild_id),
                    name=name
                ).first()
                if existing:
                    await interaction.response.send_message(
                        f"A unicycle named '{name}' already exists in this server!", 
                        ephemeral=True
                    )
                    return

            # Check if user has permission to edit
            if not (str(interaction.user.id) == unicycle.owner_id_str or await self.is_admin(interaction, session)):
                await interaction.response.send_message("You don't have permission to edit this unicycle!", ephemeral=True)
                return

            # Track what fields are being updated
            updates = []
            
            if name is not None:
                unicycle.set_name(name)
                updates.append("name")
                
            if description is not None:
                unicycle.set_description(description)
                updates.append("description")
                
            # Handle ownership changes
            if is_club_owned or owner is not None:
                # Only admins can change ownership to Club
                if is_club_owned and not await self.is_admin(interaction, session):
                    await interaction.response.send_message(
                        "Only administrators can set ownership to Club!", 
                        ephemeral=True
                    )
                    return
                
                if is_club_owned and owner:
                    await interaction.response.send_message(
                        "Cannot set both owner and club ownership. Please use only one option.", 
                        ephemeral=True
                    )
                    return
                
                # Set the new owner
                if is_club_owned:
                    new_owner_id = "Club"
                elif owner is not None:
                    new_owner_id = str(owner.id)
                else:
                    await interaction.response.send_message(
                        "No new owner specified.", 
                        ephemeral=True
                    )
                    return
                
                unicycle.set_owner_id(new_owner_id)
                
                # If the current custodian is the old owner, update custody to the new owner
                if unicycle.custody_id_str == unicycle.owner_id_str:
                    if new_owner_id != "Club":  # Only update custody if the new owner isn't Club
                        unicycle.set_custody_id(new_owner_id)
                    else:
                        # If setting to Club ownership, set custody to the person making the change
                        unicycle.set_custody_id(str(interaction.user.id))
                
                updates.append("owner to " + ("Club" if is_club_owned else str(owner)))

            if updates:
                session.commit()
                # Create a nice message about what was updated
                update_msg = "Updated " + ", ".join(updates)
                await interaction.response.send_message(
                    f"Unicycle #{unicycle_id} has been updated! {update_msg}.", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "No changes were provided to update.", 
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"Error editing unicycle: {str(e)}", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(UnicycleCommands(bot))
