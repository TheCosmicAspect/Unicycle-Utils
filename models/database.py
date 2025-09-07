from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

def get_next_guild_id(session, guild_id: str) -> int:
    """Get the next available ID for a specific guild"""
    from sqlalchemy import update
    
    sequence = session.query(GuildSequence).filter_by(guild_id=guild_id).first()
    if not sequence:
        sequence = GuildSequence(guild_id=guild_id, last_value=0)
        session.add(sequence)
        session.commit()
        current_value = 0
    else:
        current_value = sequence.last_value
    
    # Update the sequence
    new_value = current_value + 1
    stmt = update(GuildSequence).where(GuildSequence.guild_id == guild_id).values(last_value=new_value)
    session.execute(stmt)
    session.commit()
    
    return new_value
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class GuildSequence(Base):
    __tablename__ = 'guild_sequences'
    
    guild_id = Column(String, primary_key=True)
    last_value = Column(Integer, default=0, nullable=False)

class Unicycle(Base):
    __tablename__ = 'unicycles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, nullable=False)  # Discord Guild/Server ID
    guild_specific_id = Column(Integer, nullable=False)  # ID that's unique within the guild
    name = Column(String, nullable=False)
    description = Column(String)
    owner_id = Column(String, nullable=False)  # Discord User ID or "Club"
    custody_id = Column(String, nullable=False)  # Discord User ID
    
    # Make name and guild-specific ID unique within each guild
    __table_args__ = (
        UniqueConstraint('guild_id', 'name', name='_guild_name_uc'),
        UniqueConstraint('guild_id', 'guild_specific_id', name='_guild_id_uc')
    )
    
    @property
    def display_id(self) -> str:
        """Returns the guild-specific ID for display purposes"""
        return str(self.guild_specific_id)

    @property
    def name_str(self) -> str:
        return str(self.name) if self.name is not None else ""

    @property
    def description_str(self) -> str:
        return str(self.description) if self.description is not None else ""

    @property
    def owner_id_str(self) -> str:
        return str(self.owner_id) if self.owner_id is not None else ""

    @property
    def custody_id_str(self) -> str:
        return str(self.custody_id) if self.custody_id is not None else ""
    
    def set_name(self, value: str) -> None:
        self.name = value

    def set_description(self, value: str) -> None:
        self.description = value

    def set_owner_id(self, value: str) -> None:
        self.owner_id = value

    def set_custody_id(self, value: str) -> None:
        self.custody_id = value

    @property
    def guild_id_str(self) -> str:
        return str(self.guild_id) if self.guild_id is not None else ""

    def set_guild_id(self, value: str) -> None:
        self.guild_id = value

    def to_dict(self):
        return {
            'id': self.id,
            'guild_id': self.guild_id_str,
            'name': self.name_str,
            'description': self.description_str,
            'owner_id': self.owner_id_str,
            'custody_id': self.custody_id_str
        }

class AdminRole(Base):
    __tablename__ = 'admin_roles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, nullable=False)  # Discord Guild/Server ID
    role_id = Column(String, nullable=False)  # Discord Role ID
    
    # Make role_id unique within each guild
    __table_args__ = (UniqueConstraint('guild_id', 'role_id', name='_guild_role_uc'),)

# Create database and tables
engine = create_engine('sqlite:///unicycles.db')
Base.metadata.create_all(engine)

# Create session factory
Session = sessionmaker(bind=engine)
